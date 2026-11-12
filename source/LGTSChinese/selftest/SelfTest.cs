// LGTS Core 自检 —— 在游戏外逐条验规则。
//
// 这个文件不属于插件 DLL (build.cmd 只编译 Plugin.cs + Core.cs)。它和 Core.cs 一起
// 被 tools/selftest.py 单独编译成 selftest.exe, 只引用 mscorlib/System —— 没有
// UnityEngine, 没有 BepInEx, 没有游戏。所以规则改错时红的是这里, 不是玩家的屏幕。
//
// 用法: selftest.exe <report.txt> [--dump <json> <out.txt>]...
//   --dump 把 Core.ParseFlatJson 的解析结果按 Core.DumpFlat 的规范形写出来,
//   由 tools/selftest.py 与标准库 json 的结果逐字节比对(真·解析器等价性)。
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using LGTSChinese;

internal static class SelfTest
{
    private static int Cases, Fail;
    private static readonly StringBuilder Body = new StringBuilder();

    private static void Case(string name, bool ok, string detail)
    {
        Cases++;
        if (!ok) Fail++;
        Body.Append(ok ? "PASS " : "FAIL ").Append(name);
        if (!string.IsNullOrEmpty(detail)) Body.Append("  | ").Append(detail);
        Body.Append('\n');
    }

    private static void Eq(string name, string got, string want)
    {
        bool ok = got == want;
        Case(name, ok, ok ? "" : "got=" + Core.Escape(got) + " want=" + Core.Escape(want));
    }

    private static void EqN(string name, int got, int want)
    {
        Case(name, got == want, got == want ? "" : "got=" + got + " want=" + want);
    }

    private static Dictionary<string, string> Dict(params string[] kv)
    {
        var d = new Dictionary<string, string>(StringComparer.Ordinal);
        for (int i = 0; i + 1 < kv.Length; i += 2) d[kv[i]] = kv[i + 1];
        return d;
    }

    private static int Main(string[] args)
    {
        if (args.Length < 1)
        {
            Console.Error.WriteLine("usage: selftest.exe <report.txt> [--dump <json> <out.txt>]...");
            return 2;
        }
        string reportPath = args[0];

        // --dump 先跑: 它的用例数也要进报告
        int i = 1;
        while (i < args.Length)
        {
            if (args[i] != "--dump" || i + 2 >= args.Length)
            {
                Case("--dump 参数不完整", false, "位置 " + i);
                break;
            }
            string jsonPath = args[i + 1], outPath = args[i + 2];
            try
            {
                var m = new Dictionary<string, string>(StringComparer.Ordinal);
                Core.ParseFlatJson(File.ReadAllText(jsonPath, Encoding.UTF8), m);
                File.WriteAllText(outPath, Core.DumpFlat(m), new UTF8Encoding(false));
                Case("ParseFlatJson 扫完 " + Path.GetFileName(jsonPath) + " (" + m.Count + " 条)",
                     m.Count > 0, "条数 " + m.Count + "; 条数与内容由 json 比对负责");
            }
            catch (Exception e)
            {
                Case("ParseFlatJson 扫 " + Path.GetFileName(jsonPath), false, e.Message);
            }
            i += 3;
        }

        TestVersion();
        TestNorm();
        TestRefKey();
        TestParseFlatJson();
        TestCjk();
        TestNoise();
        TestRules();
        TestWrap();
        TestNumTemplate();
        TestRomance();
        TestItemGet();
        TestDump();

        var sb = new StringBuilder();
        sb.Append(Body.ToString());
        sb.Append("RESULT=").Append(Fail == 0 ? "PASS" : "FAIL")
          .Append(" cases=").Append(Cases).Append(" fail=").Append(Fail).Append('\n');
        try { File.WriteAllText(reportPath, sb.ToString(), new UTF8Encoding(false)); }
        catch (Exception e) { Console.Error.WriteLine(e.Message); return 2; }
        Console.Out.Write("cases=" + Cases + " fail=" + Fail + "\n");
        return Fail == 0 ? 0 : 1;
    }

    // ---- 版本 ----
    private static void TestVersion()
    {
        var re = new System.Text.RegularExpressions.Regex("^\\d+\\.\\d+\\.\\d+$");
        Case("VER 形如 x.y.z", re.IsMatch(Core.VER), Core.VER);
        Case("阈值: display 下限 >= 20000", Core.MinDisplayEntries >= 20000, "" + Core.MinDisplayEntries);
        Case("阈值: by_refkey 下限 >= 15000", Core.MinRefKeyEntries >= 15000, "" + Core.MinRefKeyEntries);
    }

    // ---- Norm ----
    private static void TestNorm()
    {
        Eq("Norm(null)", Core.Norm(null), null);
        Eq("Norm(\"\")", Core.Norm(""), "");
        Eq("Norm 折叠空白", Core.Norm("  a   b \t c  "), "a b c");
        Eq("Norm 剥 color 标签", Core.Norm("<color=#ff0000>red</color>"), "red");
        Eq("Norm 剥 b/i/size 标签", Core.Norm("<b>bold</b> <i>it</i> <size=120%>big</size>"), "bold it big");
        Eq("Norm <br> 不加空格", Core.Norm("A<br>B"), "AB");
        Eq("Norm 真换行变空格", Core.Norm("A\nB"), "A B");
        Eq("Norm 非标签尖括号保留", Core.Norm("a < b"), "a < b");
        Eq("Norm 颜色简写", Core.Norm("<#934494>女巫</color>"), "女巫");
        Eq("Norm sprite 标签剥掉", Core.Norm("<sprite=\"aziel\" name=\"black\">……"), "……");
        Eq("Norm 剥 U+00A0 空白", Core.Norm("\u00A0 x \u00A0"), "x");
        // 零宽空格不是空白符(不是 \s, 也不在 Trim 的判定里)—— 它由 IsNoiseOnly 负责,
        // 这里固定住这个事实, 免得有人"顺手"把它加进 Norm 而改变显示层归一键。
        Eq("Norm 不剥零宽(归噪声判定负责)", Core.Norm("a\u200Bb"), "a\u200Bb");
    }

    // ---- RefKey ----
    private static void TestRefKey()
    {
        Eq("RefKey 取斜杠之后", Core.RefKey("Dialogue/DLG_1_2_VBA_03_004"), "DLG_1_2_VBA_03_004");
        Eq("RefKey 无斜杠原样", Core.RefKey("NO_TASKS_AVAILABLE"), "NO_TASKS_AVAILABLE");
        Eq("RefKey 多斜杠只切第一个", Core.RefKey("A/B/C"), "B/C");
        Eq("RefKey null", Core.RefKey(null), null);
    }

    // ---- ParseFlatJson ----
    private static void TestParseFlatJson()
    {
        var m = Dict();
        Core.ParseFlatJson("{\"a\":\"b\",\"c\":\"d\"}", m);
        EqN("JSON 两条", m.Count, 2);
        Eq("JSON 值 a", m["a"], "b");
        Eq("JSON 值 c", m["c"], "d");

        m = Dict();
        Core.ParseFlatJson("{\n  \"a\" : \"b\" ,\n  \"c\":\"d\"\n}", m);
        EqN("JSON 空白/换行不敏感", m.Count, 2);

        m = Dict();
        Core.ParseFlatJson("{\"a\":\"x\\ny\",\"b\":\"x\\ty\",\"c\":\"q\\\"q\",\"d\":\"b\\\\s\"}", m);
        Eq("JSON \\n 转义", m["a"], "x\ny");
        Eq("JSON \\t 转义", m["b"], "x\ty");
        Eq("JSON 引号转义", m["c"], "q\"q");
        Eq("JSON 反斜杠转义", m["d"], "b\\s");

        m = Dict();
        Core.ParseFlatJson("{\"a\":\"\\u4e2d\\u6587\",\"b\":\"\\u30FB\"}", m);
        Eq("JSON \\u 转义", m["a"], "中文");
        Eq("JSON \\u30FB (中点)", m["b"], "\u30FB");

        m = Dict();
        Core.ParseFlatJson("{\"a\":\"\\uZZZZ\"}", m);
        Eq("JSON 坏 \\u 降级为字面 u", m["a"], "uZZZZ");

        m = Dict();
        Core.ParseFlatJson("{\"a\":\"tail\\", m);
        Eq("JSON 尾部孤立反斜杠", m["a"], "tail\\");

        m = Dict();
        Core.ParseFlatJson("{}", m);
        EqN("JSON 空对象", m.Count, 0);

        m = Dict();
        Core.ParseFlatJson("{\"a\":\"b\",\"a\":\"c\"}", m);
        Eq("JSON 重复键后者覆盖", m["a"], "c");

        m = Dict();
        Core.ParseFlatJson("{\"a\":\"}{\",\"b\":\"x\"}", m);
        Eq("JSON 值里含花括号", m["a"], "}{");
        Eq("JSON 花括号后继续解析", m["b"], "x");

        m = Dict();
        Core.ParseFlatJson("{\"a\":\"多行\\n值\",\"b\":\"<b>粗</b>\"}", m);
        Eq("JSON 中文值", m["a"], "多行\n值");
        Eq("JSON 带标签的值", m["b"], "<b>粗</b>");
    }

    // ---- CJK 判定 ----
    private static void TestCjk()
    {
        Case("IsCjk 汉字", Core.IsCjk('道'), "");
        Case("IsCjk 全角标点", Core.IsCjk('！'), "");
        Case("IsCjk 中点 U+30FB", Core.IsCjk('\u30FB'), "");
        Case("IsCjk 拉丁字母否", !Core.IsCjk('a'), "");
        Case("IsCjk 半角数字否", !Core.IsCjk('1'), "");
        Case("IsCjk 假名也算(区间含 3040-30FF)", Core.IsCjk('\u3042'), "u3042 落在 2E80-9FFF 内");
        Case("IsCjk 西里尔否", !Core.IsCjk('\u0416'), "");
        Case("HasCjk 混排", Core.HasCjk("hello 中文"), "");
        Case("HasCjk 纯英文", !Core.HasCjk("hello world"), "");
    }

    // ---- 噪声判定 ----
    private static void TestNoise()
    {
        Case("噪声: 空串", Core.IsNoiseOnly(""), "");
        Case("噪声: 钱数 0", Core.IsNoiseOnly("0"), "");
        Case("噪声: 钱数 1,234", Core.IsNoiseOnly("1,234"), "");
        Case("噪声: 分辨率 1920x1080", Core.IsNoiseOnly("1920x1080"), "");
        Case("噪声: 分辨率 2560×1440", Core.IsNoiseOnly("2560\u00D71440"), "");
        Case("噪声: 零宽空格", Core.IsNoiseOnly("\u200B"), "");
        Case("噪声: 省略号", Core.IsNoiseOnly("..."), "");
        Case("噪声: 全角省略号", Core.IsNoiseOnly("\u2026\u2026"), "");
        Case("噪声: 1 2 3", Core.IsNoiseOnly("1 2 3"), "");
        Case("非噪声: 拉丁串", !Core.IsNoiseOnly("Acquired"), "");
        Case("非噪声: 含数字的规则串 ROUND 3", !Core.IsNoiseOnly("ROUND 3"), "必须先被模板规则拦下");
        Case("非噪声: x22", !Core.IsNoiseOnly("x22"), "");
        Case("非噪声: 汉字", !Core.IsNoiseOnly("中文"), "");
        Case("非噪声: x 夹在一串里", !Core.IsNoiseOnly("ACQUIRED 1x"), "");
    }

    // ---- 六条模板规则 ----
    private static void TestRules()
    {
        string zh;
        // 顺序即语义: 时间戳 -> 数量角标 -> 回合 -> 续关花费 -> 日期时段 -> 单独获得
        EqN("规则 时间戳命中", (int)Core.MatchRule("DATE 2026/11/3 TIME 01:48:36", "DATE 2026/11/3 TIME 01:48:36", out zh), (int)RuleHit.SaveTime);
        Eq("规则 时间戳两行", zh, "日期 2026/11/3\n时间 01:48:36");
        Core.MatchRule("DATE 2026/11/3 TIME 01:48:36", "DATE 2026/11/3 TIME 01:48:36", out zh);
        Eq("规则 时间戳第二行是时间", zh.Split('\n')[1], "时间 01:48:36");
        Core.MatchRule("DATE 11-03-2026 TIME 1:01 AM", "DATE 11-03-2026 TIME 1:01 AM", out zh);
        Eq("规则 时间戳跟随系统区域格式", zh, "日期 11-03-2026\n时间 1:01 AM");

        Core.MatchRule("x22", "x22", out zh);
        Eq("规则 数量角标 x22", zh, "×22");
        Core.MatchRule("X1", "X1", out zh);
        Eq("规则 数量角标 X1", zh, "×1");
        EqN("规则 数量角标 5 位数字不算", (int)Core.MatchRule("x12345", "x12345", out zh), (int)RuleHit.None);
        EqN("规则 数量角标 后面带字母不算", (int)Core.MatchRule("x22kg", "x22kg", out zh), (int)RuleHit.None);

        Core.MatchRule("ROUND 3", "ROUND 3", out zh);
        Eq("规则 回合 ROUND 3", zh, "第 3 回合");
        Core.MatchRule("Round 12", "Round 12", out zh);
        Eq("规则 回合 Round 12", zh, "第 12 回合");
        EqN("规则 回合 ROUNDS 3 不算", (int)Core.MatchRule("ROUNDS 3", "ROUNDS 3", out zh), (int)RuleHit.None);

        Core.MatchRule("(5T)", "(5T)", out zh);
        Eq("规则 续关花费 (5T)", zh, "（5T）");
        Core.MatchRule("(12t)", "(12t)", out zh);
        Eq("规则 续关花费 小写 t", zh, "（12T）");
        EqN("规则 续关花费 纯括号数字不算", (int)Core.MatchRule("(5)", "(5)", out zh), (int)RuleHit.None);

        Core.MatchRule("Sat. Evening", "Sat. Evening", out zh);
        Eq("规则 日期时段 Sat. Evening", zh, "周六 傍晚");
        Core.MatchRule("Monday . Afternoon", "Monday . Afternoon", out zh);
        Eq("规则 日期时段 Monday . Afternoon(全量审计 F-02)", zh, "周一 下午");
        Core.MatchRule("Sat. Witch. Hour", "Sat. Witch. Hour", out zh);
        Eq("规则 日期时段 缩写 Witch. Hour", zh, "周六 巫魅时分");
        Core.MatchRule("Sunday\nNight", "Sunday\nNight", out zh);
        Eq("规则 日期时段 原串有换行则跟随分行", zh, "周日\n夜晚");
        EqN("规则 日期时段 缺时段不算", (int)Core.MatchRule("Sat.", "Sat.", out zh), (int)RuleHit.None);

        Core.MatchRule("Acquired 3x", "Acquired 3x", out zh);
        Eq("规则 单独获得 Acquired 3x", zh, "获得了 3 个");
        Core.MatchRule("Acquired 7", "Acquired 7", out zh);
        Eq("规则 单独获得 无 x", zh, "获得了 7 个");

        // 未命中必须放行, 不能把普通英文串误改
        foreach (var s in new[] { "ITEM GET", "Acquired 1x <color=red>Tinderbox</color>", "1920x1080",
                                 "Need something?", "Why, you...!", "..." })
        {
            EqN("规则 未命中放行: " + s, (int)Core.MatchRule(s, s, out zh), (int)RuleHit.None);
        }
        // 词典层的健在: 命中规则时 zh 一定非空
        Core.MatchRule("x9", "x9", out zh);
        Case("规则 命中时 zh 非空", !string.IsNullOrEmpty(zh), zh);
    }

    // ---- 整句包色 ----
    private static void TestWrap()
    {
        Eq("包色: 整句包裹取开标签", Core.WholeWrapOpen("<color=#ffffff>这是一句独白的话。</color>"), "<color=#ffffff>");
        Eq("包色: 非整句(前后有内容)", Core.WholeWrapOpen("我说<color=#ffffff>这句</color>"), null);
        Eq("包色: 两段包裹不算整句",
             Core.WholeWrapOpen("<color=#000000>甲段够长的一段话</color> x <color=#000000>乙段也是</color>"), null);
        Eq("包色: 无闭合", Core.WholeWrapOpen("<color=#ffffff>没有闭合的话"), null);
        Eq("包色: 内层标签不影响",
             Core.WholeWrapOpen("<color=#ff0000><b>一句足够长的恐怖台词</b></color>"), "<color=#ff0000>");
        Eq("包色: 回包", Core.RewrapColor("<color=#ff0000>一句足够长的恐怖台词</color>", "一句够长的中文台词"),
             "<color=#ff0000>一句够长的中文台词</color>");
        Eq("包色: 值已包裹不重复包",
             Core.RewrapColor("<color=#ff0000>一句足够长的恐怖台词</color>", "<color=#ff0000>中文</color>"),
             "<color=#ff0000>中文</color>");
        Eq("包色: 原文没包就不包", Core.RewrapColor("plain text", "普通中文"), "普通中文");
        Eq("包色: null 安全", Core.WholeWrapOpen(null), null);
    }

    // ---- 数字模板 ----
    private static void TestNumTemplate()
    {
        var disp = Dict("Collected fireflies: {0}", "收集到的萤火虫：{0}",
                        "You got {0} and {1}!", "你拿到了 {0} 和 {1}！");
        Eq("数字模板 单数字", Core.TryNumTemplate("Collected fireflies: 3", disp), "收集到的萤火虫：3");
        Eq("数字模板 双数字", Core.TryNumTemplate("You got 4 and 5!", disp), "你拿到了 4 和 5！");
        Eq("数字模板 无字母不模板", Core.TryNumTemplate("3", disp), null);
        Eq("数字模板 无数字不模板", Core.TryNumTemplate("Collected fireflies:", disp), null);
        Eq("数字模板 超 4 个数字不模板", Core.TryNumTemplate("1 2 3 4 5 a", disp), null);
        Eq("数字模板 词典无此模板", Core.TryNumTemplate("Nothing here 9", disp), null);
        Eq("数字模板 超长串不模板", Core.TryNumTemplate(new string('a', 305) + "1", disp), null);
    }

    // ---- 恋人弹窗 ----
    private static void TestRomance()
    {
        var disp = Dict("Rozenmarine", "萝丝玛琳", "Heart Piece Acquired!", "获得爱心碎片!");
        Eq("恋人 带 's 且双语都在",
           Core.TryRomance("Rozenmarine's Heart Piece Acquired!", disp),
           "<b>萝丝玛琳的</b>\n获得爱心碎片!");
        Eq("恋人 名字未译则保留英文",
           Core.TryRomance("Freya's Heart Piece Acquired!", disp),
           "<b>Freya的</b>\n获得爱心碎片!");
        Eq("恋人 后缀缺失走固定译",
           Core.TryRomance("Lebkuchen Strong Bond", disp),
           "<b>Lebkuchen</b>\n深厚羁绊");
        Eq("恋人 游戏错拼 Aquired 也命中",
           Core.TryRomance("Rozenmarine Heart Piece Aquired!", disp),
           "<b>萝丝玛琳</b>\n获得爱心碎片!");
        Eq("恋人 非三人不算", Core.TryRomance("Someone Heart Piece Acquired!", disp), null);
        Eq("恋人 永恒之爱", Core.TryRomance("Rozenmarine Everlasting Love!", disp),
           "<b>萝丝玛琳</b>\n永恒之爱!");
    }

    // ---- 道具复合弹窗 ----
    private static void TestItemGet()
    {
        var disp = Dict("ITEM GET", "道具获取", "Tinderbox", "火绒盒");
        var item = Dict("Tinderbox", "火绒盒", "Lebkuchen", "姜饼");
        List<string> miss;
        string r = Core.TryItemGet("ITEM GET\nAcquired 1x <color=red>Tinderbox</color>\nAcquired 2x Lebkuchen",
                                   disp, item, out miss);
        Eq("ITEM GET 三段全译", r, "道具获取\n获得了 1 个 <color=red>火绒盒</color>\n获得了 2 个 姜饼");
        EqN("ITEM GET 无漏名", miss.Count, 0);

        r = Core.TryItemGet("ITEM GET\nAcquired 1x Lebkuchen", disp, item, out miss);
        Eq("道具名表优先于整句词典(姜饼 不取 斯佩尔特)", r, "道具获取\n获得了 1 个 姜饼");

        var empty = Dict();
        r = Core.TryItemGet("Acquired 3x Nobody", empty, empty, out miss);
        Eq("未知道具名保留英文", r, "获得了 3 个 Nobody");
        EqN("未知道具名被记下", miss.Count, 1);
        Eq("未知道具名内容", miss[0], "Nobody");

        r = Core.TryItemGet("完全没有可译内容", disp, item, out miss);
        Eq("无可译返回 null", r, null);
    }

    // ---- 转储 ----
    private static void TestDump()
    {
        Eq("Escape 换行", Core.Escape("a\nb"), "a\\nb");
        Eq("Escape 制表", Core.Escape("a\tb"), "a\\tb");
        Eq("Escape 反斜杠", Core.Escape("a\\b"), "a\\\\b");
        Eq("Escape 回车", Core.Escape("a\rb"), "a\\rb");
        Eq("Escape null", Core.Escape(null), "");
        var d = Dict("b", "2", "a", "1");
        Eq("DumpFlat 按键序号排序", Core.DumpFlat(d), "a\t1\nb\t2\n");
    }
}