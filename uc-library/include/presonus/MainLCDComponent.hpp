#pragma once
#include "core/portable/corecomponent.h"
#include "core/public/corevector.h"

namespace Core::Portable {
class RootView;
}
namespace Presonus {
class MainLCDComponent;
class PageComponent;
class LcdView;
} // namespace Presonus
namespace presonus::mainlcd_port {
// Independent source-port boundary. Implementations must provide the real app
// operations; these declarations do not recover LcdView/PageComponent layouts.
struct Application {
  virtual ~Application() = default;
  virtual Presonus::PageComponent *findPage(int tag) const = 0;
  virtual void requestPage(Presonus::PageComponent *page) = 0;
  virtual void showNextPage() = 0;
  virtual int startPageTag() const = 0;
  virtual Core::Portable::RootView *rootView(Presonus::LcdView *view) const = 0;
  virtual void observeView(Presonus::LcdView *view,
                           Presonus::MainLCDComponent &observer) = 0;
};
struct State {
  Presonus::LcdView *lcd = nullptr;
  Presonus::PageComponent *current = nullptr;
  Presonus::PageComponent *next = nullptr;
  Presonus::PageComponent *back = nullptr;
  // Intentional source-port storage, independent of the original ARM layout.
  Core::FixedSizeVector<Presonus::PageComponent *, 10> backPages;
  // Stack operations opt into actual count-based state; legacy callers retain
  // their earlier independently supplied back boundary until configured.
  bool stackConfigured = false;
};
} // namespace presonus::mainlcd_port
namespace Presonus {
// Intentional CCL source port. Base and state layout are not original ARM ABI
// declarations. Return declarations absent from ELF remain pending
// verification.
class MainLCDComponent : public Core::Portable::Component {
public:
  MainLCDComponent(presonus::mainlcd_port::Application &application,
                   presonus::mainlcd_port::State &state)
      : application(application), state(state) {}
  bool hasBackPage() const;
  void pushBackPage(PageComponent *page);
  PageComponent *popBackPage();
  PageComponent *getCurrentPage() const;
  bool isEditingText() const;
  void onDestroyed(const LcdView &view);
  void setLcdView(LcdView *view);
  void stopTextInput(bool canceled) const;
  void onIdle() override;
  void showPage(int tag);
  void *castTo(int type) override;
  void showStartPage();

private:
  presonus::mainlcd_port::Application &application;
  presonus::mainlcd_port::State &state;
};
} // namespace Presonus
