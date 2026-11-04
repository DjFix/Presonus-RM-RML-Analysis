#include "presonus/MeterScaleControl.hpp"
#include "presonus/MeterControl.hpp"
#include "presonus/PanControl.hpp"
#include "presonus/surface/MuteGroupsComponent.hpp"
#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/mutable_message_event.hpp"
#include <stdexcept>

namespace Presonus {
MeterScaleControl::MeterScaleControl(const Core::Rect &rect)
    : Core::Portable::Control(rect, nullptr) {}
MeterScaleControl::~MeterScaleControl() = default;
} // namespace Presonus
