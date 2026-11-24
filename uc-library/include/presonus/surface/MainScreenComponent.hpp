#pragma once
#include "presonus/MainLCDComponent.hpp"
namespace presonus::surface {
struct MainScreenInit {};
} // namespace presonus::surface
namespace Presonus::Surface {
class MappingComponent;
// Independent tagged initialization; original returns/layout/ABI unresolved.
class MainScreenComponent : public MainLCDComponent {
public:
  explicit MainScreenComponent(presonus::surface::MainScreenInit,
                               presonus::mainlcd_port::Application &app,
                               presonus::mainlcd_port::State &state)
      : MainLCDComponent(app, state) {}
  ~MainScreenComponent() override;
  bool canGoBack(const PageComponent &, const PageComponent &) const;
  void onSelectedChannelChanged();
  int getStartPageTag() const override;
  bool displayEncoderAssignmentLocked() const;
  void pageAboutToShow(const PageComponent &, const PageComponent *);
  // Borrowed canonical provider; independent source-port binding for native
  // +f8.
  void bindMapping(MappingComponent *mapping) { mapping_ = mapping; }

  // Borrowed binding; void is a portable declaration.
  void init(MappingComponent *);

private:
  friend struct MainScreenComponentReplayAccess;
  MappingComponent *mapping_ = nullptr;
};
} // namespace Presonus::Surface
