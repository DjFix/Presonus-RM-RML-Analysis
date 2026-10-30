#pragma once
#include "core/portable/corefilename.h"
#include "core/public/corevector.h"

namespace Presonus {
// Logical source-port fields: original names/access are unknown. Their types
// and roles follow app memcpy256, two Vector<FileName> subobjects and calls.
class FileCleanup {
public:
  explicit FileCleanup(const Core::Portable::FileName &);
  ~FileCleanup();
  // Ordinary return declaration spellings remain pending; source Core add and
  // filesystem results are bool, and the original app preserves those values.
  bool addFileToRemove(const Core::Portable::FileName &);
  bool addDirectoryToRemove(const Core::Portable::FileName &);
  bool cleanup();

private:
  Core::Portable::FileName baseFolder_;
  Core::Vector<Core::Portable::FileName> files_;
  Core::Vector<Core::Portable::FileName> directories_;
};
} // namespace Presonus
