#pragma once
#include "core/portable/coresingleton.h"

namespace presonus::panel {
struct AlertManagerAccess;
}
namespace Presonus::Panel {
// Original name only: no delegate member names, return types or inheritance
// have been established. The observed two slots are bound independently below.
class IAlertDelegate;
class AlertManager : public Core::Portable::Singleton<AlertManager> {
public:
  AlertManager();
  ~AlertManager() override;
  // Portable void declarations; original ordinary returns remain pending.
  void doAlert(int, const char *, const char *, const char *, int, int);
  void dismissAlert();
  void setDelegate(IAlertDelegate *);

private:
  IAlertDelegate *delegate_;
  friend struct presonus::panel::AlertManagerAccess;
};
} // namespace Presonus::Panel

namespace presonus::panel {
// Independent source-port bridge for the original opaque delegate's first two
// virtual slots. It declares no original IAlertDelegate methods or ABI layout.
// Both callbacks must be valid whenever a nonnull delegate is installed.
struct AlertDelegateSlots {
  void (*alert)(Presonus::Panel::IAlertDelegate *, int, const char *,
                const char *, const char *, int, int) = nullptr;
  void (*dismiss)(Presonus::Panel::IAlertDelegate *) = nullptr;
};
void configureAlertDelegateSlots(AlertDelegateSlots);
// Independent integration/test access to genuine CCL singleton state. No extra
// original AlertManager or Core method is claimed by these helpers.
struct AlertManagerAccess {
  static Presonus::Panel::IAlertDelegate *
  delegate(const Presonus::Panel::AlertManager &v) {
    return v.delegate_;
  }
  static Presonus::Panel::AlertManager *current() {
    return Presonus::Panel::AlertManager::theInstance;
  }
  static void current(Presonus::Panel::AlertManager *v) {
    Presonus::Panel::AlertManager::theInstance = v;
  }
};
} // namespace presonus::panel
