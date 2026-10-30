#include "presonus/application/FileCleanup.hpp"
#include "core/portable/corefile.h"

namespace Presonus {
FileCleanup::FileCleanup(const Core::Portable::FileName &folder)
    : baseFolder_(folder), files_(0, 5), directories_(0, 5) {}
FileCleanup::~FileCleanup() = default;
bool FileCleanup::addFileToRemove(const Core::Portable::FileName &name) {
  return files_.add(name);
}
bool FileCleanup::addDirectoryToRemove(const Core::Portable::FileName &name) {
  return directories_.add(name);
}
bool FileCleanup::cleanup() {
  bool success = true;
  const int fileCount = files_.count();
  for (int i = 0; i < fileCount; ++i) {
    Core::Portable::FileName relative(files_.at(i));
    Core::Portable::FileName path(baseFolder_);
    path.descend(relative.str());
    if (Core::Portable::FileUtils::fileExists(path.str())) {
      const bool deleted = Core::Portable::FileUtils::deleteFile(path.str());
      if (success)
        success = deleted;
    }
  }
  const int directoryCount = directories_.count();
  for (int i = 0; i < directoryCount; ++i) {
    Core::Portable::FileName relative(directories_.at(i));
    Core::Portable::FileName path(baseFolder_);
    path.descend(relative.str());
    if (!Core::Portable::FileUtils::dirExists(path.str()))
      continue;
    Core::Portable::FileIterator iterator(path.str());
    while (const auto *entry = iterator.next()) {
      if (entry->directory || entry->hidden)
        continue;
      const bool deleted =
          Core::Portable::FileUtils::deleteFile(entry->name.str());
      if (success)
        success = deleted;
    }
    const bool removed = Core::Portable::FileUtils::removeDirectory(path.str());
    if (success)
      success = removed;
  }
  return success;
}
} // namespace Presonus
