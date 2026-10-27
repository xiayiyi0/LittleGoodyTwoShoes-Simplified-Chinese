Little Goody Two Shoes 简体中文汉化补丁

当前版本：v1.3.28

这是适用于 Windows 版 Little Goody Two Shoes 的简体中文运行时汉化补丁。

Notion在线双语译本https://app.notion.com/p/3ffaa7b537c180ea95aed0126e29327c

下载来源

本补丁只在 https://github.com/xiayiyi0/LittleGoodyTwoShoes-Simplified-Chinese/releases 发布。
请勿从第三方转载、网盘、群文件或“整合版”获取。

原因：本补丁依赖 winhttp.dll 把插件注入游戏进程（BepInEx 的标准做法）。代理 DLL 是杀毒软件
的常见误报对象，因此安装说明里有“把游戏目录加入信任列表”这一步——这一步是正常的，但也正
因为如此，改过包的恶意版本可以照抄同一套说辞骗玩家放行。请只从上面这个 Release 页下载，
并在解压后按包内 SHA256SUMS.txt 校验 LGTSChinese.dll 与三个词典文件。

安装方法

1. 在 Steam 库中右键 Little Goody Two Shoes，选择“管理”后选择“浏览本地文件”。
2. 将下载的压缩包完整解压到含有 LGTS.exe 的游戏根目录。
3. 允许合并 BepInEx 文件夹及覆盖同名文件。
4. 启动游戏。

安装后，游戏根目录应存在 winhttp.dll、doorstop_config.ini、arialuni_sdf_u2019 和 BepInEx 文件夹。

本补丁包含剧情与系统文本翻译、TextMeshPro 中文字体回退（含全角标点字形），以及旧版 UGUI 菜单文字的中文字体覆盖。暂停菜单右侧丝带应显示“道具、地图、设置、读取、标题画面”。

更多安装、更新、卸载与排错说明请阅读 安装说明_README.txt。

文件安全说明

本仓库不包含游戏本体、存档、运行日志、缓存或临时分析文件。补丁通过 BepInEx 在运行时加载；除替换 TextMeshPro 字体资源 arialuni_sdf_u2019（新增全角标点字形）外，不修改其他游戏资源文件。

问题反馈

提交问题时请描述游戏版本、复现步骤、实际画面与预期画面。若需要日志，请附上 BepInEx/LogOutput.log 和 BepInEx/plugins/LGTSChinese/DIAG.txt。

第三方组件

BepInEx：https://github.com/BepInEx/BepInEx
XUnity.AutoTranslator：https://github.com/bbepis/XUnity.AutoTranslator

游戏本体及其角色、文本、美术等内容的版权归原权利人所有。本仓库仅提供运行时汉化所需的插件、配置、字体资源与翻译数据。
