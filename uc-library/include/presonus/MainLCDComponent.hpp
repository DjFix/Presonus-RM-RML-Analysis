#pragma once
#include "core/portable/corecomponent.h"
#include "core/public/corevector.h"
#include <cstdint>

namespace Core::Portable {
class ContainerView;
class Control;
class RootView;
class View;
} // namespace Core::Portable
namespace Presonus {
class MainLCDComponent;
class PageComponent;
class LcdView;
} // namespace Presonus
namespace presonus::mainlcd_port {
struct ConstructionAccess;
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
  // Independent borrowed link for the native view observer slot (+0x204).
  // Bind only while the pointed-to slot outlives this component.
  Presonus::MainLCDComponent **viewObserverSlot = nullptr;
  Presonus::PageComponent *current = nullptr;
  Presonus::PageComponent *next = nullptr;
  Presonus::PageComponent *back = nullptr;
  Core::Vector<Core::Portable::View *> views;
  Core::Vector<Presonus::PageComponent *> pages;
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
  MainLCDComponent();
  ~MainLCDComponent() override;
  // Independent binding API; the borrowed application must outlive use.
  void bindApplication(presonus::mainlcd_port::Application &value) {
    application = &value;
  }
  MainLCDComponent(presonus::mainlcd_port::Application &application,
                   presonus::mainlcd_port::State &state)
      : application(&application), state(state) {}
  PageComponent *getPageByTag(int tag) const;
  void syncPageParams();
  bool hasBackPage() const;
  static void prenotifyDestroy(Core::Portable::ContainerView *container);
  void pushBackPage(PageComponent *page);
  PageComponent *popBackPage();
  PageComponent *getCurrentPage() const;
  int getCurrentPageTag() const;
  void setupBackPage();
  bool isEditingText() const;
  void onDestroyed(const LcdView &view);
  void setLcdView(LcdView *view);
  void stopTextInput(bool canceled) const;
  void onIdle() override;
  void showPage(int tag);
  void *castTo(int type) override;
  void showStartPage();
  // Portable base contract retains the existing required application boundary;
  // concrete MainScreen overrides this with its verified original default.
  virtual int getStartPageTag() const;

  // Portable default hooks. Derived screens can supply their own behavior.
  virtual void pageAboutToShow(const PageComponent &, const PageComponent *);
  virtual void onSelectedChannelChanged();
  virtual void selectedChannelUpdated();
  virtual void onFocusControlChanged(Core::Portable::Control *);

private:
  presonus::mainlcd_port::Application &requireApplication() const;
  presonus::mainlcd_port::State ownedState;
  presonus::mainlcd_port::Application *application = nullptr;
  presonus::mainlcd_port::State &state;
  // Explicit provisional observed words; no recovered semantics/layout claim.
  std::uint32_t observedWord8c = 40;
  std::uint32_t observedWordF4 = 0;
  friend struct presonus::mainlcd_port::ConstructionAccess;
};
} // namespace Presonus
