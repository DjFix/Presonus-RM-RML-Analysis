#include "presonus/mixer_dsp/FilterControllers.hpp"
#include "presonus/mixer_dsp/Dsp.hpp"
#include "presonus/mixer_dsp/FilterParameterLists.hpp"
#include <cstring>
#include <limits>

namespace {
static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
float fromBits(std::uint32_t bits) {
  float value;
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}
std::uint32_t toBits(float value) {
  std::uint32_t bits;
  std::memcpy(&bits, &value, sizeof(bits));
  return bits;
}
void update(Presonus::Dsp::FilterControllerState &state, float value,
            bool active) {
  state.valueBits = toBits(value);
  const auto previousActive = state.active;
  state.active = active ? 1 : 0;
  state.dirty = 1;
  if (!state.pending)
    state.pending = state.active ? 1 : previousActive;
}
enum class PassFilter { high, low };

bool isActive(PassFilter filter, float value) {
  if (filter == PassFilter::high)
    return value > fromBits(1103102476);
  return value < fromBits(0x469c3fff);
}
} // namespace

namespace presonus::dsp {
class FilterControllerProvider final : public Presonus::Dsp::EQController {
public:
  FilterControllerProvider(int controllerId, PassFilter filter,
                           const Presonus::Dsp::ParamDescriptorList &list)
      : EQController(1, controllerId, &list), filter_(filter) {
    portableBands().front().type = filter == PassFilter::high ? 3 : 2;
    portableEnabled() = true;
    Controller::setDefaultValues();
  }

  float getValue(int index) const override {
    return index == 0 ? fromBits(state.valueBits) : 0.f;
  }

  float setValue(int index, float value) override {
    if (index == 0) {
      update(state, value, isActive(filter_, value));
      auto &band = portableBands().front();
      band.frequency = value;
      band.dirty = state.dirty;
      band.enabled = state.active;
      sourceState().processDirty = state.pending;
    }
    return value;
  }

  Presonus::Dsp::FilterControllerState state;

private:
  PassFilter filter_;
};
} // namespace presonus::dsp

namespace Presonus::Dsp {
HiPassController::HiPassController(int controllerId)
    : provider_(std::make_shared<presonus::dsp::FilterControllerProvider>(
          controllerId, PassFilter::high,
          presonus::dsp::sourceList(*HiPassParamList::instance()))),
      state_(provider_->state) {}

LoPassController::LoPassController(int controllerId)
    : provider_(std::make_shared<presonus::dsp::FilterControllerProvider>(
          controllerId, PassFilter::low,
          presonus::dsp::sourceList(*LoPassParamList::instance()))),
      state_(provider_->state) {}

HiPassController::~HiPassController() = default;
LoPassController::~LoPassController() = default;

EQController *HiPassController::portableEQController() const {
  return provider_.get();
}

EQController *LoPassController::portableEQController() const {
  return provider_.get();
}
float HiPassController::getValue(int index) const {
  return index == 0 ? fromBits(state_.valueBits) : 0.0f;
}
float LoPassController::getValue(int index) const {
  return index == 0 ? fromBits(state_.valueBits) : 0.0f;
}
void HiPassController::setValue(int index, float value) {
  if (provider_)
    provider_->setValue(index, value);
  else if (index == 0)
    update(state_, value, isActive(PassFilter::high, value));
}
void LoPassController::setValue(int index, float value) {
  if (provider_)
    provider_->setValue(index, value);
  else if (index == 0)
    update(state_, value, isActive(PassFilter::low, value));
}
} // namespace Presonus::Dsp
