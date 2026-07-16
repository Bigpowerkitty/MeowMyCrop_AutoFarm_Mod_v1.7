源码重建说明
============

build_meow_v18.py 是确定性程序集补丁构建器，支持生成 1x、2x、5x、10x、20x、50x、500x 七个版本。

依赖：
  pip install -r requirements.txt

需要提供受支持的原版 Assembly-CSharp.dll，其 SHA256 必须为：
  ad00d6dd37d0ee222e5506e9a4b697c5b5bf10fa3673843cde68b9760654e954

环境变量：
  MEOW_SRC         原版 Assembly-CSharp.dll 的完整路径
  MEOW_BASE_ROOT   v1.7 安装包模板目录
  MEOW_OUTPUT_ROOT 新构建输出目录（不能与模板目录相同）

示例：
  set MEOW_SRC=D:\game\Assembly-CSharp.original.dll
  set MEOW_BASE_ROOT=D:\build\MeowMOD_v1.7
  set MEOW_OUTPUT_ROOT=D:\build\MeowMOD_v1.8_build
  python build_meow_v18.py

构建器会验证原版哈希、PE/CLR 元数据、关键方法体、原版手动开罐路径以及全部成品哈希；验证失败时不会生成可发布包。
