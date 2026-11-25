#pragma once
#include "core/public/corevector.h"

namespace Core::Portable {
class Component;
}
namespace Presonus::Surface {
// Portable construction and borrowed component state. Original layout and
// application roster initialization and paste serialization remain unresolved.
class FatChannelClipboard {
public:
  FatChannelClipboard();

  // Portable void declarations. The original return types remain unresolved.
  void copy(Core::Portable::Component *source);
  void
  collectPasteChannels(Core::Vector<Core::Portable::Component *> &channels);

  // Independent source-port inspection and roster binding.
  bool portableHasOwner() const { return owner_ != nullptr; }
  bool portableHasSource() const { return source_ != nullptr; }
  Core::Portable::Component *portableSource() const { return source_; }
  Core::Vector<Core::Portable::Component *> &portableRoster() {
    return roster_;
  }

  class CopyPasteFilter {
  public:
    struct SourcePortConstruction {};
    explicit CopyPasteFilter(SourcePortConstruction) {}
    // Portable bool return, not an independently recovered original return.
    bool shouldSave(int type, const char *name, void *object) const;
  };

private:
  Core::Portable::Component *owner_ = nullptr;
  Core::Portable::Component *source_ = nullptr;
  Core::Vector<Core::Portable::Component *> roster_;
};
} // namespace Presonus::Surface
