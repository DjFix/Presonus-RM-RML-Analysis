#include "presonus/MackieControlComponent.hpp"
#include "presonus/MappableMixer.hpp"
#include "presonus/color/MixerColorConverter.hpp"
#include "presonus/surface/MidiMixerHandler.hpp"
#include <cstdlib>
#include <iostream>
#include <string_view>

namespace {
void require(bool condition) {
  if (!condition)
    std::abort();
}

template <typename Receiver, typename Member, typename... Args>
[[gnu::noipa]] void dispatch(Receiver &receiver, Member member,
                             Args &&...args) {
  (receiver.*member)(static_cast<Args &&>(args)...);
}

constexpr Core::Portable::ParamInfo probe =
    PARAM_TOGGLE(34, "probe", 1, nullptr, 0);

void mackie(std::string_view task) {
  Presonus::MackieControlComponent component;
  component.addParameters(&probe, 1);
  auto *parameter = component.getParameterByTag(34);
  component.model.connectionState = 33;
  component.model.touched[2] = 81;
  component.masterFader = nullptr;
  const auto prohibit = [](auto &&...) { std::abort(); };
  component.model.midiSink = prohibit;
  component.model.ledSink = prohibit;
  component.model.textSink = prohibit;
  for (const int value : {-1, 0, 31}) {
    if (task == "r06") {
      component.Presonus::MackieControlComponent::updateDisplayStyle(
          34, value, value != 0);
      dispatch(component, &Presonus::MackieControlComponent::updateDisplayStyle,
               34, value, value != 0);
    } else {
      component.Presonus::MackieControlComponent::updateLedColor(34, value);
      dispatch(component, &Presonus::MackieControlComponent::updateLedColor, 34,
               value);
    }
    require(parameter->getValue() == 1.f && component.countParameters() == 1 &&
            component.model.connectionState == 33 &&
            component.model.touched[2] == 81 &&
            component.masterFader == nullptr);
  }
}

struct Services : presonus::surface::midi_port::Services {
  void setDefaultColor(const std::string &) override { std::abort(); }
  bool recordParameterPresent() override { std::abort(); }
  float recordParameterValue() override { std::abort(); }
  void updateRecordMapping(bool) override { std::abort(); }
  bool idleSlotPresent(unsigned) override { std::abort(); }
  void invokeIdleSlot(unsigned) override { std::abort(); }
};

void midi(std::string_view task) {
  namespace Surface = Presonus::Surface;
  Core::Portable::Component parameters;
  parameters.addParameters(&probe, 1);
  auto *parameter = parameters.getParameterByTag(34);
  Services services;
  presonus::surface::midi_port::State state;
  state.localParameters = &parameters;
  state.normalParameters = &parameters;
  state.enabled = true;
  state.accumulation[3] = 47;
  state.activeMapping = 2;
  Surface::MidiMixerHandler handler(state, services);
  if (task == "s15") {
    for (auto *argument :
         {parameter, static_cast<Core::Portable::Parameter *>(nullptr)}) {
      handler.Surface::MidiMixerHandler::onMappingParamChanged(argument);
      dispatch(handler, &Surface::MidiMixerHandler::onMappingParamChanged,
               argument);
    }
  } else {
    handler.Surface::MidiMixerHandler::updatePanEncoderConnection();
    dispatch(handler, &Surface::MidiMixerHandler::updatePanEncoderConnection);
  }
  require(state.localParameters == &parameters &&
          state.normalParameters == &parameters && state.enabled &&
          state.accumulation[3] == 47 && state.activeMapping == 2 &&
          parameter->getValue() == 1.f && parameters.countParameters() == 1);
}

struct Observer : Presonus::IMixerComponentObserver {
  int observed = 103;
};

void observe(std::string_view task) {
  using O = Presonus::IMixerComponentObserver;
  Observer observer;
  if (task == "s17") {
    observer.O::onSelectionChanged();
    dispatch(observer, &O::onSelectionChanged);
  } else if (task == "s18") {
    for (int value : {-1, 0, 11}) {
      auto message = static_cast<O::ObjectChangeMessage>(value);
      observer.O::onObjectChanged(message);
      dispatch(observer, &O::onObjectChanged, message);
    }
  } else {
    const O::ReplaceArgs args;
    observer.O::onComponentReplaced(args);
    dispatch(observer, &O::onComponentReplaced, args);
  }
  require(observer.observed == 103);
}

struct Converter : MixerColorConverter {
  explicit Converter(int &destroyed) : destroyed_(destroyed) {}
  ~Converter() override { ++destroyed_; }

private:
  int &destroyed_;
};

void color() {
  int destroyed = 0;
  {
    Converter first(destroyed), second(destroyed);
    Presonus::MappableMixer mixer;
    require(mixer.getColorConverter() == nullptr);
    {
      Presonus::MappableMixer independent;
      for (Presonus::IColorConverter *expected :
           {static_cast<Presonus::IColorConverter *>(&first),
            static_cast<Presonus::IColorConverter *>(&second),
            static_cast<Presonus::IColorConverter *>(nullptr)}) {
        dispatch(independent, &Presonus::MappableMixer::setColorConverter,
                 expected);
        require(independent.getColorConverter() == expected);
        require(mixer.getColorConverter() == nullptr);
      }
      independent.setColorConverter(&first);
    }
    require(destroyed == 0);
    mixer.setColorConverter(&second);
    require(mixer.getColorConverter() == &second);
  }
  require(destroyed == 2);
}
} // namespace

int main(int argc, char **argv) {
  require(argc == 2);
  const std::string_view task = argv[1];
  if (task.starts_with("r"))
    mackie(task);
  else if (task == "s13" || task == "s14")
    color();
  else if (task == "s15" || task == "s16")
    midi(task);
  else
    observe(task);
  std::cout << task << " typed host replay passed\n";
}
