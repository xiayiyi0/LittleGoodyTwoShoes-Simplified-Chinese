Little Goody Two Shoes 简体中文汉化补丁 v1.3.26

一、补丁说明

本补丁适用于 Windows 版 Little Goody Two Shoes。

补丁通过 BepInEx 在运行时加载，不修改游戏原始资源文件。主要包含：

1. 剧情、对话、事件与多数游戏内文本的简体中文翻译。
2. 主菜单、暂停菜单、设置、存档、地图、日志、道具等系统 UI 的中文化。
3. TextMeshPro 中文字体回退，以及旧版 UGUI Text 的系统中文字体替换。
4. 道具获取复合弹窗、日期时段文本、彩色富文本等运行时显示路径的兼容处理。
5. 字体资源 arialuni_sdf_u2019 已扩充全角标点字形（，！？：（）—…），对话不再使用半角规避标点。

当前实装版本：LGTS Simplified Chinese v1.3.26。

二、安装方法

1. 在 Steam 库中右键 Little Goody Two Shoes。
2. 选择“管理” -> “浏览本地文件”。
3. 打开后应能看到 LGTS.exe；这个文件夹就是游戏根目录。
4. 将压缩包内所有文件和文件夹完整解压到游戏根目录。
5. 如果系统询问是否合并文件夹或覆盖同名文件，选择“是”或“全部替换”。
6. 启动游戏。

安装完成后，游戏根目录至少应包含：

- LGTS.exe
- winhttp.dll
- doorstop_config.ini
- arialuni_sdf_u2019
- BepInEx 文件夹

重要：不要只复制 BepInEx/plugins/LGTSChinese。字体、BepInEx 启动器、AutoTranslator 与中文词典都需要一并保留。

三、首次启动与确认方法

首次启动会加载插件与字体，可能比原版略慢，属于正常现象。

进入游戏后，主菜单、暂停菜单、对话和设置菜单应显示中文。要确认插件已正确加载，可查看：

BepInEx/LogOutput.log

日志中应包含类似内容：

Loading [LGTS Simplified Chinese 1.3.26]
LGTS 中文插件已加载
Loaded fallback font for TextMesh Pro: arialuni_sdf_u2019

版本自检（反馈问题前请先完成以下三条，并在反馈中附上结果）：

1. 插件版本：在文件管理器中右键 BepInEx/plugins/LGTSChinese/LGTSChinese.dll，
   选“属性”→“详细信息”，文件版本应为 1.3.26.0。
2. 诊断日志首行：用记事本打开 BepInEx/plugins/LGTSChinese/DIAG.txt（运行过一次
   游戏后生成），首行应为 “=== LGTS DIAG v1.3.26 启动 ===”。
3. 文件完整性：对照发布包内的 SHA256SUMS.txt，可用命令
   certutil -hashfile "文件路径" SHA256
   逐条核对（至少核对 LGTSChinese.dll 与两个 translation 词典）。

反馈问题时请随附 BepInEx/plugins/LGTSChinese/DIAG.txt 与 BepInEx/LogOutput.log，
并在正文中注明：游戏版本（Steam 客户端可见）、补丁版本（上述第 1/2 条）、
复现步骤、截图或录屏。

四、暂停菜单丝带文字验收

本版本已为旧版 UGUI Text 配置中文字体覆盖。打开暂停菜单时，右侧丝带应显示：

- 道具
- 地图
- 设置
- 读取
- 标题画面

锁定项目保留锁图标是正常的。如果“标题画面”在个别分辨率下显得过宽，可在：

BepInEx/Translation/zh/Text/UI_System.txt

将：

Title=标题画面

改为：

Title=标题

保存后重启游戏即可生效。

五、更新方法

下载新版本后，将新压缩包完整解压到同一游戏根目录并覆盖旧文件即可。更新时请不要保留旧版的 LGTSChinese.dll、translation 文件或 AutoTranslator 配置文件。

六、卸载方法

删除以下由补丁添加的项目即可恢复原版游戏文件：

- winhttp.dll
- doorstop_config.ini
- .doorstop_version（如存在）
- arialuni_sdf_u2019
- BepInEx 文件夹

这些文件均不属于游戏本体；删除它们不会删除存档。存档仍由 Steam 与游戏原有位置管理。

七、常见问题

1. 游戏完全没有变化

确认 winhttp.dll、doorstop_config.ini、arialuni_sdf_u2019 和 BepInEx 文件夹都在含 LGTS.exe 的同一层目录；不要多嵌套一层压缩包目录。然后检查 BepInEx/LogOutput.log 是否生成。

2. 中文显示为方块或空白

确认 arialuni_sdf_u2019 没有遗漏，并确认 BepInEx/config/AutoTranslatorConfig.ini 中保留：

FallbackFontTextMeshPro=arialuni_sdf_u2019
OverrideFont=Microsoft YaHei

如果你的系统精简掉了“Microsoft YaHei”，请安装微软雅黑或改用已安装的中文字体名称，然后重启游戏。

3. 暂停菜单右侧丝带仍然空白

首先确认 AutoTranslatorConfig.ini 中的 OverrideFont=Microsoft YaHei 没有被清空。若仍无效，请将 BepInEx/LogOutput.log 与 BepInEx/plugins/LGTSChinese/DIAG.txt 一并提交反馈。

4. 杀毒软件阻止启动或隔离文件

BepInEx 需要通过 winhttp.dll 将插件注入 Unity 游戏。请检查杀毒软件隔离区并将游戏目录加入信任列表后重新解压补丁。

注意：本补丁只在 GitHub 仓库的 Release 页发布
（https://github.com/xiayiyi0/LittleGoodyTwoShoes-Simplified-Chinese/releases）。
“加信任列表”这一步本身是正常的，但第三方转载的“整合版”“绿色版”可以照抄这段说明，
让玩家为真正有害的文件放行。放行之前请先确认压缩包来源，并按包内 SHA256SUMS.txt
校验 LGTSChinese.dll 与三个词典文件；来源不明时不要加信任，直接删掉重下。

5. Steam 验证文件后补丁失效

Steam 验证完整性可能移除或还原注入文件。验证完成后重新解压补丁即可。

6. 游戏本体更新后补丁失效或出现异常

本补丁通过钩子挂钩游戏自身的本地化取词接口，游戏本体更新可能改变这些接口，
表现为：部分文本回到英文、整段无翻译、或个别界面显示异常（一般不导致崩溃）。

处理顺序：

a. 先确认补丁文件还在。游戏更新有时会覆盖 arialuni_sdf_u2019 与 BepInEx 文件夹，
   按“二、安装方法”重新把补丁完整解压到游戏根目录覆盖一次。

b. 再看日志定位。打开 BepInEx/LogOutput.log，搜索 “LGTS Simplified Chinese”：
   - 没有 “LGTS 中文插件已加载” → 插件根本没加载，多半是 a. 没做到位或 BepInEx 被覆盖。
   - 有加载但出现 “未找到 I2.Loc.LocalizationManager”、“未挂上任何取词方法”、
     或若干条 “未找到 ... DoLocalize” → 游戏改了内部接口，当前补丁版本不兼容，
     需要等补丁更新，重装没有用。

c. 把 LogOutput.log 与 DIAG.txt 一并提交反馈，并注明游戏版本号。游戏版本可以在
   主菜单界面或 Steam 库的属性中看到。

如果你不希望游戏自动更新，可在 Steam 库中右键游戏 →“属性”→“更新”，
把自动更新改为“只在启动游戏时更新”，需要时再手动更新。

八、文件说明

- BepInEx/plugins/LGTSChinese：本补丁的运行时汉化插件与词典。
- BepInEx/plugins/XUnity.AutoTranslator：非 I2 UI 文本翻译与字体回退组件。
- BepInEx/Translation/zh/Text：系统 UI 静态中文词典。
- arialuni_sdf_u2019：TextMeshPro 中文字体资源。
- BepInEx/config/AutoTranslatorConfig.ini：字体与文本框架配置。

九、第三方组件

本补丁随包使用下列开源组件：

- BepInEx：插件加载框架。
  https://github.com/BepInEx/BepInEx
- XUnity.AutoTranslator：UI 文本处理与字体回退。
  https://github.com/bbepis/XUnity.AutoTranslator

游戏本体、角色、文本与美术版权归原权利人所有。本补丁仅提供运行时汉化所需的配置、插件和翻译数据，不包含游戏本体文件。
