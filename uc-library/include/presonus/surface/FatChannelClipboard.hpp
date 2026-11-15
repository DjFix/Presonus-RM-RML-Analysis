#pragma once
namespace Presonus::Surface {
// Partial original scope only; no recovered clipboard lifecycle/interface
// claim.
class FatChannelClipboard {
public:
  class CopyPasteFilter {
  public:
    struct SourcePortConstruction {};
    explicit CopyPasteFilter(SourcePortConstruction) {}
    // Portable bool return, not an independently recovered original return.
    bool shouldSave(int type, const char *name, void *object) const;
  };
};
} // namespace Presonus::Surface
