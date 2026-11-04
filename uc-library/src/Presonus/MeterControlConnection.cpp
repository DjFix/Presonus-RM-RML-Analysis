#include "presonus/MeterControl.hpp"
#include "presonus/MeterScaleControl.hpp"
#include "presonus/PanControl.hpp"
#include "presonus/surface/MuteGroupsComponent.hpp"
#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/mutable_message_event.hpp"
#include <stdexcept>

namespace Presonus {
MeterControl::MeterControl(const Core::Rect &rect)
    : Core::Portable::Control(rect, nullptr) {}
void MeterControl::connect(void *object) {
  Core::Portable::Control::connect(object);
  if (auto *p = getParameter())
    setValue(p->getNormalized());
}
} // namespace Presonus
