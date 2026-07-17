Little Goody Two Shoes 简体中文汉化补丁 v1.3.10

一、补丁说明

本补丁适用于 Windows 版 Little Goody Two Shoes。

补丁通过 BepInEx 在运行时加载，不修改游戏原始资源文件。主要包含：

1. 剧情、对话、事件与多数游戏内文本的简体中文翻译。
2. 主菜单、暂停菜单、设置、存档、地图、日志、道具等系统 UI 的中文化。
3. TextMeshPro 中文字体回退，以及旧版 UGUI Text 的系统中文字体替换。
4. 道具获取复合弹窗、日期时段文本、彩色富文本等运行时显示路径的兼容处理。

当前实装版本：LGTS Simplified Chinese v1.3.10。

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

Loading [LGTS Simplified Chinese 1.3.10]
LGTS 中文插件已加载
Loaded fallback font for TextMesh Pro: arialuni_sdf_u2019

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

5. Steam 验证文件后补丁失效

Steam 验证完整性可能移除或还原注入文件。验证完成后重新解压补丁即可。

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
