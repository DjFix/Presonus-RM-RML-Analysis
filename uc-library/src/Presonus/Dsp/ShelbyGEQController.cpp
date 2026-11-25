#include "core/public/corestringbuffer.h"
#include "presonus/dsp/ControllerInfo.hpp"
#include "presonus/mixer_dsp/Dsp.hpp"
#include "presonus/mixer_dsp/GEQParameterList.hpp"
#include <algorithm>
#include <cstring>
#include <stdexcept>
namespace Presonus::Dsp {
ShelbyGEQController::ShelbyGEQController() : ShelbyGEQController(0, 0) {}
ShelbyGEQController::ShelbyGEQController(int channel, int controllerId)
    : Controller(controllerId,
                 &presonus::dsp::sourceList(*GEQParamList::instance())),
      channel_(channel) {
  markers_.fill(0xff);
}
ShelbyGEQController::~ShelbyGEQController() = default;
float ShelbyGEQController::setValue(int index, float value) {
  if (index > 32)
    return 0.f;
  if (index < 0)
    throw std::out_of_range("Unchecked original negative index");
  auto &stored = values_[static_cast<unsigned>(index)];
  if (stored != value) {
    if (index == 32)
      markers_.fill(0xff);
    stored = value;
    sourceState().processDirty = 1;
  }
  return stored;
}
void ShelbyGEQController::printValue(Presonus::StringResult &result, int,
                                     float value) const {
  Core::CStringBuffer<128> formatted;
  formatted.appendFormat("%.2f", static_cast<double>(value * 100.f));
  if (result.buffer && result.capacity > 0) {
    const auto length = std::min(static_cast<std::size_t>(result.capacity - 1),
                                 std::strlen(formatted.str()));
    std::memcpy(result.buffer, formatted.str(), length);
    result.buffer[length] = '\0';
  }
}
void ShelbyGEQController::getParameterInfo(ParamInfo &info, int index) const {
  Controller::getParameterInfo(info, index);
}
void ShelbyGEQController::setupProcess(const SetupProperty &property) {
  Controller::setupProcess(property);
}
float ShelbyGEQController::getValue(int index) const {
  if (index > 32)
    return 0.f;
  if (index < 0)
    throw std::out_of_range("Unchecked original negative index");
  return values_[static_cast<unsigned>(index)];
}
int ShelbyGEQController::getNumParameters() const { return 33; }
} // namespace Presonus::Dsp
