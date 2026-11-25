#include "presonus/mixer_dsp/FilterControllers.hpp"
#include "presonus/dsp/ControllerInfo.hpp"
#include "presonus/mixer/AudioComponent.hpp"
#include "presonus/mixer_dsp/Dsp.hpp"
#include "presonus/mixer_dsp/EqSourceProviders.hpp"
#include "presonus/mixer_dsp/FilterParameterLists.hpp"
#include <bit>
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
class FilterControllerProvider final
    : public Presonus::Dsp::EQController,
      public Presonus::dspcomponent_port::Boundary {
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

  void bind(Presonus::Mixer::AudioComponent &audio) {
    component_ = &audio.coreComponent();
    audio.bind(*this);
  }

  int count(Presonus::Dsp::IController &controller) override {
    return controller.getNumParameters();
  }
  float value(Presonus::Dsp::IController &controller, int tag) override {
    return controller.getValue(tag);
  }
  void set(Presonus::Dsp::IController &controller, int tag,
           float value) override {
    controller.setValue(tag, value);
  }
  unsigned flags(Presonus::Dsp::IController &) override {
    return sourceState().word20;
  }
  void acknowledge(Presonus::Dsp::IController &controller) override {
    controller.flushParameterChanges();
  }
  bool readout(Presonus::Dsp::IController &controller, int ordinal) override {
    Presonus::Dsp::ParamInfo info{};
    controller.getParameterInfo(info, ordinal);
    return (info.flags & 1u) != 0;
  }
  int load(const Core::Portable::InputStorage &storage) override {
    return component_->load(storage);
  }
  void idle() override { component_->onIdle(); }
  void changed(Core::Portable::Parameter *parameter, int reason) override {
    component_->paramChanged(parameter, reason);
  }

  Presonus::Dsp::FilterControllerState state;

private:
  PassFilter filter_;
  Core::Portable::Component *component_ = nullptr;
};

namespace {
using Core::Portable::ParamInfo;
using Presonus::Dsp::ParamDescriptorList;
using Presonus::Mixer::AudioComponent;

// The app's two XMen tables are individually bound to the native constructor
// literal references. CCL borrows these process-lifetime records.
constexpr ParamInfo hiPassParameter{ParamInfo::kFloat,
                                    0,
                                    "hpf",
                                    24.f,
                                    1000.f,
                                    0.f,
                                    24.f,
                                    std::bit_cast<float>(0x3b03126fu),
                                    0x4a,
                                    "freq.0/off",
                                    "log",
                                    nullptr,
                                    "Hi Pass Filter",
                                    "HI PASS Filter"};
constexpr ParamInfo loPassParameter{ParamInfo::kFloat,
                                    0,
                                    "lpf",
                                    100.f,
                                    20000.f,
                                    0.f,
                                    20000.f,
                                    std::bit_cast<float>(0x3b03126fu),
                                    0x4a,
                                    "freq.0/~/off",
                                    "log",
                                    nullptr,
                                    "Lo Pass Filter",
                                    nullptr};

std::unique_ptr<AudioComponent>
makeAudioComponent(const char *name, Core::IPropertyHandler *handler,
                   int controllerId, int channelId, PassFilter filter,
                   const ParamDescriptorList &descriptors,
                   const ParamInfo &parameter) {
  auto controller = std::make_unique<FilterControllerProvider>(
      controllerId, filter, descriptors);
  auto audio = std::make_unique<AudioComponent>(name, controller.get(), handler,
                                                channelId);
  auto *provider = controller.release();
  provider->bind(*audio);

  auto &component = audio->coreComponent();
  component.addParameters(&parameter, 1, false);
  audio->parameters().push_back(component.getParameterAt(0));
  audio->syncValues(true);
  return audio;
}
} // namespace

std::unique_ptr<Presonus::Mixer::AudioComponent>
makeHiPassAudioComponent(const char *name, Core::IPropertyHandler *handler,
                         int controllerId, int channelId) {
  registerEqSourcePortProviders();
  return makeAudioComponent(
      name, handler, controllerId, channelId, PassFilter::high,
      sourceList(*Presonus::Dsp::HiPassParamList::instance()), hiPassParameter);
}

std::unique_ptr<Presonus::Mixer::AudioComponent>
makeLoPassAudioComponent(const char *name, Core::IPropertyHandler *handler,
                         int controllerId, int channelId) {
  registerEqSourcePortProviders();
  return makeAudioComponent(
      name, handler, controllerId, channelId, PassFilter::low,
      sourceList(*Presonus::Dsp::LoPassParamList::instance()), loPassParameter);
}
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
