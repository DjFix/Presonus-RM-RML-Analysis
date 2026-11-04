#include "presonus/mixer/FXBusComponent.hpp"
#include "presonus/mixer/GEQLinkHandler.hpp"
#include "presonus/mixer/GlobalComponent.hpp"
#include "presonus/mixer/RackMixerComponent.hpp"
#include "presonus/mixer/SendOutputComponent.hpp"
#include <iomanip>
#include <iostream>
#include <memory>
#include <new>
#include <stdexcept>
#include <type_traits>

namespace {
struct NamingServices final : presonus::mixer::ChannelApplicationServices {
  bool isLinked(const Presonus::Mixer::ChannelComponent &) const override {
    throw std::logic_error("unused naming boundary");
  }
  void removeLink(Presonus::Mixer::ChannelComponent &) override {
    throw std::logic_error("unused naming boundary");
  }
  Presonus::Mixer::ChannelComponent *
  linkablePair(Presonus::Mixer::ChannelComponent &) override {
    throw std::logic_error("unused naming boundary");
  }
  void faderLocateDirty(Presonus::Mixer::ChannelComponent &) override {
    throw std::logic_error("unused naming boundary");
  }
  void coefficientsChanged(Presonus::Mixer::ChannelComponent &, bool) override {
    throw std::logic_error("unused naming boundary");
  }
};
int destroyed, deleted, arraysDestroyed, arraysDeleted;
struct Child : Core::Portable::Component {
  ~Child() override { ++destroyed; }
  static void operator delete(void *p) noexcept {
    ++deleted;
    ::operator delete(p);
  }
};
struct Array : Core::Portable::TComponentArray<Child> {
  explicit Array(int n) : TComponentArray(n) {}
  ~Array() override { ++arraysDestroyed; }
  static void operator delete(void *p) noexcept {
    ++arraysDeleted;
    ::operator delete(p);
  }
};
template <class T> void lifecycle(int count) {
  destroyed = deleted = arraysDestroyed = arraysDeleted = 0;
  alignas(T) unsigned char storage[sizeof(T)];
  T *component = new (storage) T;
  for (int i = 0; i < count; ++i)
    component->addChild(new Child);
  component->addChildren(new Array(count));
  // Explicit complete destruction: no parent operator delete is requested.
  component->~T();
  std::cout << destroyed << ' ' << deleted << ' ' << arraysDestroyed << ' '
            << arraysDeleted << '\n';
}
void state(const presonus::send_output_port::SendState &s) {
  std::cout << s.sendChanged << ' ' << s.output.outputCoeffChanged << ' '
            << s.childChanged << ' ' << s.output.updatePending << ' ';
}
} // namespace
int main() {
  int target, tag, message, count, dirty, mutate;
  std::uint32_t initial;
  while (std::cin >> target >> tag >> message >> count >> initial >> dirty >>
         mutate) {
    if (target == 1 || target == 10) {
      Core::Portable::Component parameters;
      Core::Portable::ParamInfo info{};
      info.type = Core::Portable::ParamInfo::kFloat;
      info.tag = 5;
      info.minValue = 0;
      info.maxValue = 3;
      parameters.addParameters(&info, 1);
      parameters.getParameterByTag(5)->setValue(tag ? 2.f : 0.f);
      Presonus::Mixer::MixerComponentBase base;
      base.cascadeParameters = &parameters;
      NamingServices services;
      std::vector<presonus::mixer::ChannelState> channelStates(count);
      std::vector<std::unique_ptr<Presonus::Mixer::ChannelComponent>> channels;
      std::vector<std::unique_ptr<Core::Portable::Component>> owners;
      const Core::Portable::ParamInfo names[] = {PARAM_STRING(0, "number", 0),
                                                 PARAM_STRING(1, "label", 0),
                                                 PARAM_STRING(2, "name", 0)};
      for (int i = 0; i < count; ++i) {
        channels.push_back(std::make_unique<Presonus::Mixer::ChannelComponent>(
            channelStates[i], services));
        owners.push_back(std::make_unique<Core::Portable::Component>());
        owners.back()->addParameters(names, 3);
        owners.back()->getParameterByTag(0)->fromString("old number", false);
        owners.back()->getParameterByTag(1)->fromString("old label", false);
        const auto name = (i % 2 ? "Custom " : "Ch. ") + std::to_string(i + 1);
        owners.back()->getParameterByTag(2)->fromString(name.c_str(), false);
        base.inputChannels.add(channels.back().get());
      }
      base.hardwareMicLineInputs = count;
      auto index = [&](auto *c) {
        for (int i = 0; i < count; ++i)
          if (channels[i].get() == c)
            return i;
        throw std::logic_error("unbound naming channel");
      };
      base.channelIdentity = [&](auto *c) {
        return std::pair<int, int>{0, index(c)};
      };
      base.bindInputChannelNaming(
          [&](auto *c) { return owners[index(c)].get(); });
      base.cascadeStatePending = true;
      std::uint32_t value = initial;
      Presonus::Mixer::RackMixerComponent rack(base, value);
      if (target == 1)
        rack.onCascadeStateChange();
      else
        base.onCascadeStateChange();
      std::cout << value << ' ' << base.cascadeStatePending << ' '
                << base.isSlave();
      for (auto &owner : owners)
        for (int i = 0; i < 3; ++i) {
          char text[256]{};
          owner->getParameterByTag(i)->toString(text, 256);
          std::cout << ' ' << std::quoted(text);
        }
      std::cout << '\n';
    } else if (target == 2) {
      presonus::mixer::ChannelState channel;
      presonus::output_port::Bindings output{channel, {}, {}, false,
                                             0,       0,  {}, {}};
      output.outputCoeffChanged = initial;
      output.updatePending = dirty;
      presonus::send_output_port::SendState own{output, initial, initial};
      std::vector<presonus::mixer::ChannelState> channels(count);
      std::vector<std::unique_ptr<presonus::output_port::Bindings>>
          childBindings;
      std::vector<std::unique_ptr<presonus::send_output_port::SendState>>
          childStates;
      std::vector<presonus::send_output_port::SendState *> children;
      for (int i = 0; i < count; ++i) {
        auto b = std::make_unique<presonus::output_port::Bindings>(
            presonus::output_port::Bindings{
                channels[i], {}, {}, false, 0, 0, {}, {}});
        b->outputCoeffChanged = initial;
        b->updatePending = dirty;
        auto s = std::make_unique<presonus::send_output_port::SendState>(
            presonus::send_output_port::SendState{*b, initial, initial});
        children.push_back(s.get());
        childStates.push_back(std::move(s));
        childBindings.push_back(std::move(b));
      }
      Core::Portable::ParamInfo info{};
      info.type = Core::Portable::ParamInfo::kInt;
      info.tag = tag;
      Core::Portable::NumericParam parameter(info);
      int calls = 0, observedTag = 0, observedMessage = 0;
      std::vector<std::uint32_t> observedStates;
      output.channelParamChanged = [&](Core::Portable::Parameter *p, int msg) {
        if (p != &parameter)
          throw 1;
        auto capture = [&](const auto &s) {
          observedStates.push_back(s.sendChanged);
          observedStates.push_back(s.output.outputCoeffChanged);
          observedStates.push_back(s.childChanged);
          observedStates.push_back(s.output.updatePending);
        };
        capture(own);
        for (auto *child : children)
          capture(*child);
        ++calls;
        observedTag = p->getTag();
        observedMessage = msg;
        if (mutate) {
          info.tag = tag == 14 ? 400 : 14;
          own.sendChanged = own.childChanged = 9;
          output.outputCoeffChanged = 9;
          output.updatePending = false;
        }
      };
      Presonus::Mixer::OutputComponent base(output);
      Presonus::Mixer::SendOutputComponent send(base, own, children);
      send.paramChanged(&parameter, message);
      state(own);
      for (auto *child : children)
        state(*child);
      std::cout << calls << ' ' << observedTag << ' ' << observedMessage;
      for (auto value : observedStates)
        std::cout << ' ' << value;
      std::cout << '\n';
    } else if (target == 3)
      lifecycle<Presonus::Mixer::GlobalComponent>(count);
    else if (target == 4)
      lifecycle<Presonus::Mixer::GEQLinkHandler>(count);
    else if (target == 30)
      lifecycle<Core::Portable::Component>(count);
    else
      return 2;
  }
}
