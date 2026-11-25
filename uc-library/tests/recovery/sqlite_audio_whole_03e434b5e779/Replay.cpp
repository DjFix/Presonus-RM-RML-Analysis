#include "core/public/coreformatter.h"
#include "presonus/dsp/ControllerInfo.hpp"
#include "presonus/mixer/AudioComponent.hpp"
#include "presonus/mixer/HPFilterComponent.hpp"
#include "presonus/mixer/LPFilterComponent.hpp"
#include "presonus/mixer_dsp/Dsp.hpp"

#include <array>
#include <bit>
#include <cstddef>
#include <iomanip>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string_view>

extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __real__ZdlPvm(void *, std::size_t) noexcept;

namespace {
using Core::Portable::NumericParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Presonus::Dsp::EQController;
using Presonus::Mixer::HPFilterComponent;
using Presonus::Mixer::LPFilterComponent;

struct Events {
  const void *controller = nullptr;
  const void *component = nullptr;
  std::array<int, 8> order{};
  std::size_t size = 0;
  void append(int event) { order.at(size++) = event; }
};

Events *activeEvents = nullptr;
void noteDelete(const void *object) {
  if (activeEvents && object == activeEvents->controller)
    activeEvents->append(2);
  if (activeEvents && object == activeEvents->component)
    activeEvents->append(4);
}

struct Handler final : Core::IPropertyHandler {
  explicit Handler(Events &events) : events(events) {}
  void setProperty(const Core::Property &) override {}
  void getProperty(Core::Property &) override {}
  void release() override { events.append(1); }
  Events &events;
};

struct ParameterObserver final : Core::Portable::ParamObserverBase {
  explicit ParameterObserver(Events &events) : events(events) {}
  void paramChanged(Parameter *parameter, int message) override {
    if (message == Parameter::kDestroyed) {
      events.append(3);
      parameter->removeObserver(this);
    }
  }
  Events &events;
};

template <typename Filter> struct DerivedFilter : Filter {
  using Filter::Filter;
};

void verify(bool condition, const char *message) {
  if (!condition)
    throw std::runtime_error(message);
}

unsigned bits(float value) { return std::bit_cast<unsigned>(value); }

template <typename Filter>
void replay(int controllerId, int channelId, const char *unit,
            std::string_view curve, unsigned deltaBits) {
  Events events;
  Handler handler(events);
  ParameterObserver observer(events);
  alignas(Filter) std::array<std::byte, sizeof(Filter) + 2 * alignof(Filter)>
      object{};
  object.front() = std::byte{0xa5};
  object.back() = std::byte{0x5a};
  auto *filter = new (object.data() + alignof(Filter))
      Filter("filter-channel", &handler, controllerId, channelId);
  auto *audio = filter->portableAudioComponent();
  verify(audio, "missing audio");
  auto &component = audio->coreComponent();
  verify(std::string_view(component.getName()) == "filter-channel",
         "audio name");
  auto *provider = dynamic_cast<EQController *>(audio->getController());
  verify(provider && provider->sourceState().target == &handler &&
             provider->sourceState().byte1d == 0 && events.size == 0,
         "target borrow/adoption");
  verify(provider->getNumBands() == 1 && provider->getNumParameters() == 1,
         "provider count");
  auto *parameter = component.getParameterAt(0);
  verify(parameter && audio->parameters().size() == 1 &&
             parameter == audio->parameters().front() &&
             parameter == component.getParameterByTag(parameter->getTag()),
         "CCL parameter identity");
  verify(parameter->getController() == &component && !parameter->isOwnInfo(),
         "CCL observer and descriptor ownership");
  verify(parameter->getFormatter() == Core::FormatterRegistry::find(unit),
         "CCL formatter binding");
  auto *numeric = NumericParam::cast(parameter);
  verify(numeric && numeric->getInterpolator() &&
             numeric->getInterpolator()->getName() == curve,
         "CCL float interpolator");

  unsigned flags = (parameter->isBipolar() ? ParamInfo::kBipolar : 0) |
                   (parameter->isStorable() ? ParamInfo::kStorable : 0) |
                   (!parameter->isPublic() ? ParamInfo::kPrivate : 0) |
                   (parameter->isLinkable() ? ParamInfo::kLinkable : 0) |
                   (parameter->isMutable() ? ParamInfo::kMutable : 0) |
                   (parameter->isReadOnly() ? ParamInfo::kReadOnly : 0) |
                   (parameter->isUserFlag1() ? ParamInfo::kUserFlag1 : 0) |
                   (parameter->isUserFlag2() ? ParamInfo::kUserFlag2 : 0);
  auto &band = provider->portableBands().front();
  Presonus::Dsp::ParamInfo info{};
  provider->getParameterInfo(info, 0);
  verify(bits(provider->getValue(0)) == bits(band.frequency) &&
             bits(band.frequency) == bits(parameter->getValue()),
         "initial synchronization");
  std::cout << provider->sourceState().constructorId << ' '
            << std::bit_cast<int>(provider->sourceState().word04) << ' '
            << component.countParameters() << ' ' << audio->readoutCount()
            << ' ' << info.flags << ' ' << band.type << ' '
            << provider->portableEnabled() << ' ' << int(band.dirty) << ' '
            << int(band.enabled) << ' '
            << int(provider->sourceState().processDirty) << ' '
            << bits(parameter->getValue()) << ' ' << parameter->getType() << ' '
            << parameter->getTag() << ' ' << bits(parameter->getMin()) << ' '
            << bits(parameter->getMax()) << ' '
            << bits(numeric->getInterpolator()->getMidRange()) << ' '
            << bits(parameter->getDefault()) << ' ' << flags << ' '
            << std::quoted(parameter->getName()) << ' '
            << std::quoted(parameter->getTitle()) << ' '
            << std::quoted(parameter->getTitle(true)) << '\n';

  const float delta = std::bit_cast<float>(deltaBits);
  const bool fromMin = parameter->getValue() == parameter->getMin();
  const float afterStep =
      numeric->normalizedToRange(fromMin ? delta : 1.f - delta);
  if (fromMin)
    parameter->increment();
  else
    parameter->decrement();
  verify(bits(parameter->getValue()) == bits(afterStep),
         "CCL normalized delta");
  audio->syncValues(false);

  const float changed = (parameter->getMin() + parameter->getMax()) * .5f;
  provider->setValue(0, changed);
  audio->syncReadouts();
  verify(bits(parameter->getValue()) != bits(changed), "readout exclusion");
  audio->syncValues(false);
  verify(bits(parameter->getValue()) == bits(changed),
         "live provider synchronization");
  parameter->addObserver(&observer);
  events.controller = provider;
  events.component = filter;
  activeEvents = &events;
  filter->~Filter();
  activeEvents = nullptr;
  verify(events.size == 3 && events.order[0] == 1 && events.order[1] == 2 &&
             events.order[2] == 3,
         "handler release, controller deletion, CCL parameter destruction");
  verify(object.front() == std::byte{0xa5} && object.back() == std::byte{0x5a},
         "complete destruction retains receiver storage");
  std::cout
      << "handler-release controller-deallocation ccl-parameter-destruction\n";
}
} // namespace

extern "C" void __wrap__ZdlPv(void *object) noexcept {
  noteDelete(object);
  __real__ZdlPv(object);
}
extern "C" void __wrap__ZdlPvm(void *object, std::size_t size) noexcept {
  noteDelete(object);
  __real__ZdlPvm(object, size);
}

int main(int argc, char **argv) {
  if (argc != 8)
    return 2;
  try {
    std::string_view kind(argv[1]);
    std::string_view variant(argv[2]);
    const int controller = std::stoi(argv[3]);
    const int channel = std::stoi(argv[4]);
    const unsigned delta = std::stoul(argv[7]);
    if (kind == "HP") {
      if (variant == "C2")
        replay<DerivedFilter<HPFilterComponent>>(controller, channel, argv[5],
                                                 argv[6], delta);
      else
        replay<HPFilterComponent>(controller, channel, argv[5], argv[6], delta);
    } else if (kind == "LP") {
      if (variant == "C2")
        replay<DerivedFilter<LPFilterComponent>>(controller, channel, argv[5],
                                                 argv[6], delta);
      else
        replay<LPFilterComponent>(controller, channel, argv[5], argv[6], delta);
    } else {
      return 2;
    }
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
