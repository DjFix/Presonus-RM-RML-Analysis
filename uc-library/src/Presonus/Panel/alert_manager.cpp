#include "presonus/panel/alert_manager.hpp"

DEFINE_SINGLETON(Presonus::Panel::AlertManager)

namespace {
presonus::panel::AlertDelegateSlots slots;
}
namespace presonus::panel {
void configureAlertDelegateSlots(AlertDelegateSlots value) { slots = value; }
} // namespace presonus::panel
namespace Presonus::Panel {
AlertManager::AlertManager() : delegate_(nullptr) {}
// Conditional current-instance clearing comes from the actual pinned CCL
// Singleton destructor; do not reproduce Core bodies from the old binary.
AlertManager::~AlertManager() = default;
void AlertManager::setDelegate(IAlertDelegate *value) { delegate_ = value; }
void AlertManager::doAlert(int kind, const char *a, const char *b,
                           const char *c, int x, int y) {
  if (delegate_)
    slots.alert(delegate_, kind, a, b, c, x, y);
}
void AlertManager::dismissAlert() {
  if (delegate_)
    slots.dismiss(delegate_);
}
} // namespace Presonus::Panel
