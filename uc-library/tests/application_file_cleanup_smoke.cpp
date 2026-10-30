#include "presonus/application/FileCleanup.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const auto base = std::filesystem::absolute(argv[1]).lexically_normal();
  if (std::filesystem::exists(base))
    return 3;
  std::filesystem::create_directories(base / "cache" / "nested");
  std::ofstream(base / "one.tmp") << "owned test file";
  std::ofstream(base / "cache" / "visible.tmp") << "owned test file";
  std::ofstream(base / "cache" / ".hidden") << "owned test file";
  Core::Portable::FileName folder(base.c_str());
  Presonus::FileCleanup first(folder);
  if (!first.addFileToRemove(Core::Portable::FileName("one.tmp")) ||
      !first.addDirectoryToRemove(Core::Portable::FileName("cache")))
    return 4;
  if (first.cleanup())
    return 5;
  if (std::filesystem::exists(base / "one.tmp") ||
      std::filesystem::exists(base / "cache" / "visible.tmp") ||
      !std::filesystem::exists(base / "cache" / ".hidden") ||
      !std::filesystem::is_directory(base / "cache" / "nested"))
    return 6;
  // Remove only fixture objects created above, never walk an existing tree.
  std::filesystem::remove(base / "cache" / ".hidden");
  std::filesystem::remove(base / "cache" / "nested");
  Presonus::FileCleanup second(folder);
  second.addDirectoryToRemove(Core::Portable::FileName("cache"));
  if (!second.cleanup() || std::filesystem::exists(base / "cache"))
    return 7;
  std::cout << "actual CCL cleanup smoke passed; original ARM differential "
               "still pending\n";
}
