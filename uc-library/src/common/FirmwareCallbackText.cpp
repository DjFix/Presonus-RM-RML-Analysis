#include "presonus/surface_update/CallbackText.hpp"
namespace presonus::surface_update {
void setCallbackText(Core::Portable::Component &component, const char *title,
                     const char *message) {
  if (auto *p = component.countParameters() > 0 ? component.getParameterByTag(2)
                                                : nullptr)
    p->fromString(title, false);
  if (auto *p = component.countParameters() > 0 ? component.getParameterByTag(3)
                                                : nullptr)
    p->fromString(message, false);
}
void setCallbackAlert(Core::Portable::Component &component, const char *alert,
                      const char *title, const char *message) {
  if (auto *p = component.countParameters() > 0 ? component.getParameterByTag(1)
                                                : nullptr)
    p->fromString(alert, false);
  setCallbackText(component, title, message);
}
} // namespace presonus::surface_update
