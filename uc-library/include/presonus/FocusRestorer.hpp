#pragma once
#include "core/portable/gui/coreview.h"
#include "core/public/corestringbuffer.h"
#include <array>
#include <cstdint>
namespace Presonus {
// Portable source model; original member types and ARM layout remain
// unresolved.
class FocusRestorer {
public:
  explicit FocusRestorer(Core::Portable::ContainerView &container);
  ~FocusRestorer();
  struct FocusInfo {
    FocusInfo();
    void setView(Core::Portable::View &view);
    std::array<std::uint32_t, 7> observedState;
    Core::CStringBuffer<32> name;
  };
  const FocusInfo &sourcePortSnapshot() const noexcept { return snapshot_; }
  class FindFilter : public Core::Portable::ViewFilter {
  public:
    explicit FindFilter(const FocusInfo &info) : info(info) {}
    bool matches(const Core::Portable::View *view) const override;

  private:
    const FocusInfo &info;
  };

private:
  Core::Portable::ContainerView
      &container_; // borrowed; must outlive this object
  FocusInfo snapshot_;
};
} // namespace Presonus
