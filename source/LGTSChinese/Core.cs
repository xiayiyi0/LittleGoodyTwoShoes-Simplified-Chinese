// LGTS Core —— 零 Unity 依赖的译本引擎。
//
// 为什么单独一个文件 (v1.3.33 结构侧):
//   旧版把 Norm / ParseFlatJson / 六条模板规则全塞在 Plugin.cs 里, 而 Plugin.cs 依赖
//   UnityEngine / BepInEx / Harmony —— 结果这些纯逻辑**只能在游戏里跑**才能验证,
//   出错的表现是"进游戏某一屏显示不对", 反馈周期以分钟计, 而且要人眼去看。
//   把它们搬到这里以后, selftest.exe 用同一份源码单独编译成控制台程序 (不引用任何
//   Unity 程序集), 在 CI/本地 0.2 秒跑完几十条用例 —— 规则改错会先在这里红, 不会
//   等到玩家进游戏才红。
//
// 分层约定:
//   Core.cs    只允许 using System.*  —— 不得出现 UnityEngine / BepInEx / Harmony。
//              任何新加的规则, 先在这里写成纯函数 + 在 selftest/SelfTest.cs 里补用例。
//   Plugin.cs  Harmony 钩子、Unity 组件、DIAG 落盘的接线层; 规则一律问 Core。
//
// 自检:  python tools/selftest.py            (编译 + 跑用例 + 落盘报告)
//        报告在 tools/acceptance/selftest_v<VER>.txt, verify_release.py 的 I 组会验它。
using System;
using System.Collections.Generic;
using System.Text;
using System.Text.RegularExpressions;

namespace LGTSChinese
{
    // 六条模板规则命中的是哪一条。None = 都不命中, 交给词典层。
    internal enum RuleHit
    {
        None = 0,
        SaveTime,     // "DATE 2026/11/3 TIME 01:48:36"      存档位时间戳
        QtySuffix,    // "x22"                                数量角标
        Round,        // "ROUND 3" / "Round 3"                小游戏回合
        RetryCost,    // "(5T)"                               小游戏续关花费
        DayTime,      // "Sat. Evening"                       日期+时段
        Acquired,     // "Acquired 3x"                        单独获得提示
    }

    internal static class Core
    {
        // 版本号的唯一来源。Plugin.VER 直接引用它, 构建脚本 / DIAG / selftest 报告
        // 全部由这里派生 —— 升版本只改这一行。
        internal const string VER = "1.3.33";

        // v1.3.27 (G3): 显示词典条数下限。低于此值说明文件被截断或解析半途失败,
        // 旧版会静默带病运行(玩家看到大面积英文, 日志却只有一行"载入 N 条")。
        internal const int MinDisplayEntries = 20000;
        // v1.3.31: 译文表(by_refkey)同样要有下限 —— 旧版只有 display 有自检, 这张表
        // 载入 0 条也能"正常"启动, 玩家看到全英文而日志只有一行载入失败。
        internal const int MinRefKeyEntries = 15000;

        // ---- 归一化 ----
        // 去富文本标签 + 折叠空白, 作为显示层匹配键。含 </...> 与 <#rrggbb> 颜色简写。
        // 注意 <br> 是**直接删除**, 不替换成空格: "A<br>B" 归一成 "AB", 与 "A B" 不同。
        internal static readonly Regex TagRe = new Regex("<[/#a-zA-Z][^>]*>");
        internal static readonly Regex WsRe = new Regex("\\s+");

        internal static string Norm(string s)
        {
            if (string.IsNullOrEmpty(s)) return s;
            if (s.IndexOf('<') >= 0) s = TagRe.Replace(s, "");   // 无标签则跳过正则(P2-03 提速)
            s = WsRe.Replace(s, " ");
            return s.Trim();
        }

        // ---- RefKey 归一: I2 term key = "Category/RefKey"; 取 '/' 之后 ----
        internal static string RefKey(string term)
        {
            if (string.IsNullOrEmpty(term)) return term;
            int slash = term.IndexOf('/');
            return slash >= 0 ? term.Substring(slash + 1) : term;
        }

        // ---- 极简 JSON 平表解析(键值均为字符串), 避免引入额外依赖 ----
        // 容错边界见 v1.3.17 (C5): 孤立尾部反斜杠按字面量输出; \u 剩余不足 4 位或非
        // 十六进制时降级为字面 'u', 不再抛异常(此前畸形转义会让整张译文表加载失败)。
        internal static void ParseFlatJson(string s, Dictionary<string, string> outMap)
        {
            int i = 0, n = s.Length;
            Func<char, bool> ws = c => c == ' ' || c == '\t' || c == '\r' || c == '\n';
            Func<string> readStr = () =>
            {
                while (i < n && s[i] != '"') i++;
                i++; // opening quote
                var sb = new StringBuilder();
                while (i < n)
                {
                    char c = s[i++];
                    if (c == '\\')
                    {
                        if (i >= n) { sb.Append(c); break; }
                        char e = s[i++];
                        switch (e)
                        {
                            case 'n': sb.Append('\n'); break;
                            case 'r': sb.Append('\r'); break;
                            case 't': sb.Append('\t'); break;
                            case '"': sb.Append('"'); break;
                            case '\\': sb.Append('\\'); break;
                            case '/': sb.Append('/'); break;
                            case 'u':
                                if (i + 4 <= n && IsHex4(s, i))
                                { sb.Append((char)Convert.ToInt32(s.Substring(i, 4), 16)); i += 4; }
                                else sb.Append(e);
                                break;
                            default: sb.Append(e); break;
                        }
                    }
                    else if (c == '"') break;
                    else sb.Append(c);
                }
                return sb.ToString();
            };
            while (i < n && s[i] != '{') i++;
            i++;
            while (i < n)
            {
                while (i < n && ws(s[i])) i++;
                if (i < n && s[i] == '}') break;
                if (i >= n || s[i] != '"') break;
                string key = readStr();
                while (i < n && s[i] != ':') i++;
                i++;
                while (i < n && ws(s[i])) i++;
                string val = readStr();
                outMap[key] = val;
                while (i < n && s[i] != ',' && s[i] != '}') i++;
                if (i < n && s[i] == ',') { i++; continue; }
                if (i < n && s[i] == '}') break;
            }
        }

        internal static bool IsHex4(string s, int pos)
        {
            for (int k = pos; k < pos + 4; k++)
            {
                char h = s[k];
                bool ok = (h >= '0' && h <= '9') || (h >= 'a' && h <= 'f') || (h >= 'A' && h <= 'F');
                if (!ok) return false;
            }
            return true;
        }

        // ---- CJK 判定 ----
        // 含全角/CJK 标点。范围: CJK 部首+统一汉字 / 全角字符 / CJK 标点。
        internal static bool IsCjk(char c)
        {
            return c >= '\u2E80' && c <= '\u9FFF' || c >= '\uFF00' && c <= '\uFFEF'
                   || c >= '\u3000' && c <= '\u303F';
        }

        internal static bool HasCjk(string s)
        {
            for (int i = 0; i < s.Length; i++) if (IsCjk(s[i])) return true;
            return false;
        }

        // ---- 噪声判定: 这一串根本不需要译文 ----
        // v1.3.31 (结构审查 F-02): 纯数字/标点/空白/零宽的写入(钱数 0-999、零宽空格等)
        // 根本不需要译文, 旧版却把它们全记成 [TMP MISS]: 一次运行 1,002 条 uniqMiss 里
        // 1,001 条是 HUD 钱数, 真正的英文漏译被埋掉, "0 miss" 发布门槛事实上不可判定。
        // 白名单式判定: 任何其它字符(拉丁/假名/西里尔/汉字…)都返回 false, 即照旧记
        // [TMP MISS], 避免把真实漏译误判成噪声而静默吞掉。
        // v1.3.32: 设置菜单的分辨率项 "1920x1080" 由 Screen.resolutions 动态生成, 每个
        // 玩家的显示器都不同, 根本没法定值 —— 只在这种「数字 x 数字」整串形态下放行。
        internal static readonly Regex ResolutionRe = new Regex("^\\d{2,5}\\s*[xX\\u00D7]\\s*\\d{2,5}$");

        internal static bool IsNoiseOnly(string s)
        {
            if (string.IsNullOrEmpty(s)) return true;
            if (ResolutionRe.IsMatch(s.Trim())) return true;
            for (int i = 0; i < s.Length; i++)
            {
                char c = s[i];
                if (c >= '0' && c <= '9') continue;              // 半角数字
                if (c <= 0x20) continue;                          // 空格/控制符
                if (c == '\u00A0' || c == '\u3000') continue;     // 不换行空格/全角空格
                if (c == '\u200B' || c == '\u200C' || c == '\u200D' || c == '\uFEFF') continue; // 零宽/BOM
                if (c >= '\uFF10' && c <= '\uFF19') continue;     // 全角数字
                switch (c)
                {
                    case '.': case ',': case ':': case ';': case '/': case '\\': case '|':
                    case '%': case '+': case '-': case '_': case '=': case '*': case '\u00D7': case '\u00F7':
                    case '(': case ')': case '[': case ']': case '{': case '}': case '<': case '>':
                    case '\'': case '"': case '`': case '^': case '~': case '@': case '#': case '&': case '$':
                    case '!': case '?': case '\u2026': case '\u00B7': case '\u2014': case '\u2013':
                    case '\u201C': case '\u201D': case '\u2018': case '\u2019':
                        continue;
                }
                return false;
            }
            return true;
        }

        // ---- 六条模板规则 ----
        // 这些都是"运行时拼出来的串", 词典不可能穷举, 只能按规则改写。全部纯函数,
        // 参数只有 (归一后的键, 原始串), 没有任何 Unity/IO 依赖 —— 这正是 selftest
        // 能在游戏外逐条验的东西。
        // v1.3.32: 存档位时间戳 "DATE 2026/11/3 TIME 01:48:36" (SaveSlots/.../Info/SaveTime)。
        // 日期格式随系统区域变, 所以两段都用 .+? 兜住, 只认 DATE/TIME 两个词。
        internal static readonly Regex SaveTimeRe = new Regex("^DATE\\s+(.+?)\\s+TIME\\s+(.+)$");
        // v1.3.32: 背包/食材列表的数量角标 "x22" (ItemView(Clone)/Quantity)。数量无上限。
        internal static readonly Regex QtySuffixRe = new Regex("^[xX]\\s*(\\d{1,4})$");
        // v1.3.32: 小游戏回合数 "ROUND 3" 与 "Round 3" 两种写法都在, 数字无上限。
        internal static readonly Regex RoundRe = new Regex("^ROUND\\s+(\\d+)$", RegexOptions.IgnoreCase);
        // v1.3.32: 小游戏续关花费 "(5T)" (Minigame.cs:152 retryCost)。T 是游戏内货币记号,
        // 原样保留, 只把半角括号换成全角(与其余五层口径一致)。
        internal static readonly Regex RetryCostRe = new Regex("^\\((\\d+)\\s*[Tt]\\)$");
        // 日期+时段模板 (P0-3): 支持全称/缩写、点/空格分隔。
        // v1.3.7 (C2): 补 "Witch. Hour" —— 存档槽用 WitchingHourAbv 的缩写形态(SaveSlot.cs:274)。
        internal static readonly Regex DayTimeRe = new Regex(
            "^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sun\\.|Mon\\.|Tue\\.|Wed\\.|Thu\\.|Fri\\.|Sat\\.)\\s*\\.?\\s*(Morning|Afternoon|Evening|Night|Dawn|Dusk|Noon|Daytime|Witching Hour|Witch\\. Hour)$",
            RegexOptions.IgnoreCase);
        // 单独 "Acquired {n}x" (P1-01)
        internal static readonly Regex AcquiredRe = new Regex("^Acquired\\s+(\\d+)\\s*[xX]?$");
        // v1.3.7 (C2): 数字模板抠取
        internal static readonly Regex NumRe = new Regex("\\d+");
        // v1.3.7 (C2): 恋人弹窗归一键 "名字['s] 后缀"。名字 = 三位恋爱对象(Constants.LoveInterests);
        // 后缀 = UI 表 HEART_ACQUIRED / MAX_LOVE_ACQUIRED / STRONG_BOND_ACQUIRED 的英文,
        // "Ac?quired" 同时覆盖游戏正拼与实机曾出现的错拼。
        internal static readonly Regex RomanceRe = new Regex(
            "^(Rozenmarine|Freya|Lebkuchen)('s)?\\s+(Heart Piece Ac?quired!|Everlasting Love!|Strong Bond)$",
            RegexOptions.IgnoreCase);
        // 道具复合行: "Acquired 1x <color=red>Tinderbox</color>" (P0-2)
        internal static readonly Regex AcqItemRe = new Regex(
            "^Acquired\\s+(\\d+)\\s*[xX]\\s*(<color=[^>]+>)?\\s*(.+?)\\s*(</color>)?\\s*$");
        // v1.3.30 (F2): HUD 小提示的道具名+数量拼接串 "Lebkuchen x5" (ItemGetSmall/Name)。
        internal static readonly Regex ItemQtyRe = new Regex("^(.+?)\\s*[xX\u00D7]\\s*(\\d+)$");

        internal static readonly Dictionary<string, string> DayMap =
            new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            {"Sunday","周日"},{"Sun.","周日"},{"Monday","周一"},{"Mon.","周一"},{"Tuesday","周二"},{"Tue.","周二"},
            {"Wednesday","周三"},{"Wed.","周三"},{"Thursday","周四"},{"Thu.","周四"},{"Friday","周五"},{"Fri.","周五"},
            {"Saturday","周六"},{"Sat.","周六"},
        };
        internal static readonly Dictionary<string, string> TimeMap =
            new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            {"Morning","上午"},{"Afternoon","下午"},{"Evening","傍晚"},{"Night","夜晚"},{"Dawn","黎明"},
            {"Dusk","黄昏"},{"Noon","正午"},{"Daytime","白天"},{"Witching Hour","巫魅时分"},{"Witch. Hour","巫魅时分"},
        };

        // 模板规则的统一入口: 命中返回规则名并给出中文, 未命中返回 None 且 zh=null。
        // orig 只用于一件事 —— 判断原串里是否已有真换行(日期+时段要跟随原文分行)。
        // 顺序敏感: 与 v1.3.32 实机 DIAG 的判定顺序逐条一致, 改顺序等于改上屏结果。
        internal static RuleHit MatchRule(string key, string orig, out string zh)
        {
            zh = null;
            Match m = SaveTimeRe.Match(key);
            if (m.Success)
            {
                // v1.3.32 (同日第 7 次替换): 日期与时间必须分行。存档槽的文本框按字符换行,
                // 单行串在中文下会在「时/间」中间断掉 (实机截图 2026-11-04 23:03)。
                zh = "日期 " + m.Groups[1].Value.Trim() + "\n时间 " + m.Groups[2].Value.Trim();
                return RuleHit.SaveTime;
            }
            m = QtySuffixRe.Match(key);
            if (m.Success) { zh = "×" + m.Groups[1].Value; return RuleHit.QtySuffix; }
            m = RoundRe.Match(key);
            if (m.Success) { zh = "第 " + m.Groups[1].Value + " 回合"; return RuleHit.Round; }
            m = RetryCostRe.Match(key);
            if (m.Success) { zh = "（" + m.Groups[1].Value + "T）"; return RuleHit.RetryCost; }
            m = DayTimeRe.Match(key);
            if (m.Success)
            {
                string dd, tt;
                if (DayMap.TryGetValue(m.Groups[1].Value, out dd) && TimeMap.TryGetValue(m.Groups[2].Value, out tt))
                {
                    string sep = (orig != null && orig.IndexOf('\n') >= 0) ? "\n" : " ";
                    zh = dd + sep + tt;
                    return RuleHit.DayTime;
                }
            }
            m = AcquiredRe.Match(key);
            if (m.Success) { zh = "获得了 " + m.Groups[1].Value + " 个"; return RuleHit.Acquired; }
            return RuleHit.None;
        }

        // DIAG 标签。保持与 v1.3.32 实机 DIAG 原文逐字相同, 老 DIAG 仍可直接比对。
        internal static string RuleLabel(RuleHit rk)
        {
            switch (rk)
            {
                case RuleHit.SaveTime: return "SAVETIME HIT";
                case RuleHit.QtySuffix: return "QTY SUFFIX";
                case RuleHit.Round: return "ROUND HIT";
                case RuleHit.RetryCost: return "RETRY COST";
                case RuleHit.DayTime: return "DAYTIME HIT";
                case RuleHit.Acquired: return "ACQUIRED HIT";
            }
            return "RULE HIT";
        }

        // ---- 整句包色检测与回包 ----
        // v1.3.7 (C1): 检测整句被单一 <color=...>...</color> 包裹(思考独白 thoughtColor /
        // 恐怖台词 horrorColor 由 DialogueWindow 运行时整句包色)。返回开标签, 未包裹返回 null。
        // 深度扫描: 外层开标签若在结尾之前就被闭合(如 "<c>A</c> x <c>B</c>")则不算整句包裹。
        internal static string WholeWrapOpen(string s)
        {
            if (s == null || s.Length < 16 || s[0] != '<') return null;
            if (!s.StartsWith("<color=", StringComparison.OrdinalIgnoreCase)) return null;
            if (!s.EndsWith("</color>", StringComparison.OrdinalIgnoreCase)) return null;
            int gt = s.IndexOf('>');
            if (gt < 0) return null;
            int endTag = s.Length - 8;   // 末尾 "</color>" 的起点
            int depth = 1, i = gt + 1;
            while (i < s.Length)
            {
                int lt = s.IndexOf('<', i);
                if (lt < 0) break;
                if (lt + 8 <= s.Length && string.Compare(s, lt, "</color>", 0, 8, StringComparison.OrdinalIgnoreCase) == 0)
                {
                    depth--;
                    if (depth == 0) return lt == endTag ? s.Substring(0, gt + 1) : null;
                    i = lt + 8;
                }
                else if (lt + 6 <= s.Length && string.Compare(s, lt, "<color", 0, 6, StringComparison.OrdinalIgnoreCase) == 0)
                {
                    depth++; i = lt + 6;
                }
                else i = lt + 1;
            }
            return null;
        }

        // 原串整句包色而词典值不含运行时包裹时回包。同时修复 LogMenu 对恐怖行的
        // ReplaceFirstOccurrence(text, horrorCode, ...) —— 回包后译文重新含 horrorColor hex。
        internal static string RewrapColor(string orig, string zh)
        {
            string open = WholeWrapOpen(orig);
            if (open == null) return zh;
            if (WholeWrapOpen(zh) != null) return zh;   // 词典值已整句包裹, 不重复包
            return open + zh + "</color>";
        }

        // ---- 词典相关的纯函数(词典由调用方传入, 本类不持有任何全局状态) ----
        // v1.3.7 (C2): 数字模板 —— 把 key 中的数字串依次替换为 {0},{1}... 查词典模板键。
        internal static string TryNumTemplate(string key, Dictionary<string, string> disp)
        {
            if (key == null || key.Length > 300) return null;
            bool hasDigit = false, hasAlpha = false;
            for (int i = 0; i < key.Length; i++)
            {
                char c = key[i];
                if (char.IsDigit(c)) hasDigit = true;
                else if (char.IsLetter(c)) hasAlpha = true;
            }
            if (!hasDigit || !hasAlpha) return null;   // 纯数字/无字母串不模板化
            var nums = new List<string>();
            string tpl = NumRe.Replace(key, delegate(Match m)
            {
                nums.Add(m.Value);
                return "{" + (nums.Count - 1) + "}";
            });
            if (nums.Count > 4) return null;
            string zh;
            if (!(disp.TryGetValue(tpl, out zh) && !string.IsNullOrEmpty(zh))) return null;
            for (int i = 0; i < nums.Count; i++) zh = zh.Replace("{" + i + "}", nums[i]);
            return zh;
        }

        // v1.3.7 (C2): 恋人弹窗两段式。实机与反编译存在两种形态(带 's + 原版错拼 "Aquired" /
        // 不带 's + "Acquired"), 正则同时覆盖; 名字与后缀分别查词典, 后缀缺失用固定译兜底。
        internal static string TryRomance(string key, Dictionary<string, string> disp)
        {
            var m = RomanceRe.Match(key);
            if (!m.Success) return null;
            string name = m.Groups[1].Value;
            bool poss = m.Groups[2].Success && m.Groups[2].Value.Length > 0;
            string tail = m.Groups[3].Value;
            string zhName, zhTail;
            if (!(disp.TryGetValue(name, out zhName) && !string.IsNullOrEmpty(zhName))) zhName = name;
            if (!(disp.TryGetValue(tail, out zhTail) && !string.IsNullOrEmpty(zhTail)))
            {
                if (tail.StartsWith("Heart Piece", StringComparison.OrdinalIgnoreCase)) zhTail = "获得爱心碎片!";
                else if (tail.StartsWith("Everlasting", StringComparison.OrdinalIgnoreCase)) zhTail = "永恒之爱!";
                else zhTail = "深厚羁绊";
            }
            return "<b>" + zhName + (poss ? "的" : "") + "</b>\n" + zhTail;
        }

        // 道具名取值 —— 专用表优先, 整句词典兜底(未命中返回 null, 由调用方决定行为)。
        internal static string LookupItemName(string key, Dictionary<string, string> disp,
                                             Dictionary<string, string> itemNames)
        {
            if (string.IsNullOrEmpty(key)) return null;
            string zh;
            if (itemNames != null && itemNames.TryGetValue(key, out zh) && !string.IsNullOrEmpty(zh)) return zh;
            if (disp != null && disp.TryGetValue(key, out zh) && !string.IsNullOrEmpty(zh)) return zh;
            return null;
        }

        // 逐行翻译道具复合串, 保留换行与颜色标签 (P0-2)。
        // missingNames 收集"道具名既不在专用表也不在整句词典"的英文, 由调用方写 DIAG。
        internal static string TryItemGet(string s, Dictionary<string, string> disp,
                                          Dictionary<string, string> itemNames, out List<string> missingNames)
        {
            missingNames = new List<string>();
            var lines = s.Replace("\r", "").Split('\n');
            bool any = false;
            for (int i = 0; i < lines.Length; i++)
            {
                string ln = lines[i].Trim();
                if (ln.Length == 0) continue;
                var m = AcqItemRe.Match(ln);
                if (m.Success)
                {
                    string cnt = m.Groups[1].Value;
                    string colorOpen = m.Groups[2].Value;   // <color=red> 或 ""
                    string name = m.Groups[3].Value;
                    // v1.3.18 (F1) / v1.3.30 (F2): 道具上下文优先查专用映射 —— Lebkuchen 在道具位
                    // 是"姜饼"而非角色名"斯佩尔特"; 未命中再回退 display 词典。
                    string zhName = LookupItemName(Norm(name), disp, itemNames);
                    if (zhName == null) { zhName = name; missingNames.Add(name); }
                    string colorClose = string.IsNullOrEmpty(colorOpen) ? "" : "</color>";
                    lines[i] = "获得了 " + cnt + " 个 " + colorOpen + zhName + colorClose;
                    any = true; continue;
                }
                string zh;
                if (disp != null && disp.TryGetValue(Norm(ln), out zh) && !string.IsNullOrEmpty(zh))
                { lines[i] = zh; any = true; }
            }
            return any ? string.Join("\n", lines) : null;
        }

        // ---- 规范化转储: 给 selftest 做"C# 解析器 == 调用方 JSON 解析器"的逐字节比对 ----
        // 键按序号排序(Ordinal), 值把 \\ \n \r \t 转义回单行, 每行 "键<TAB>值"。
        internal static string DumpFlat(Dictionary<string, string> m)
        {
            var keys = new List<string>(m.Keys);
            keys.Sort(StringComparer.Ordinal);
            var sb = new StringBuilder();
            for (int i = 0; i < keys.Count; i++)
            {
                sb.Append(keys[i]).Append('\t').Append(Escape(m[keys[i]])).Append('\n');
            }
            return sb.ToString();
        }

        internal static string Escape(string s)
        {
            if (s == null) return "";
            var sb = new StringBuilder(s.Length + 8);
            for (int i = 0; i < s.Length; i++)
            {
                char c = s[i];
                switch (c)
                {
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default: sb.Append(c); break;
                }
            }
            return sb.ToString();
        }
    }
}