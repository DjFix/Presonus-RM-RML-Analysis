#include "core/public/corestringbuffer.h"
#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/PanelRegistrar.hpp"
#include "presonus/panel/switch_control.hpp"
#include <cassert>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <vector>
using namespace Presonus::Panel;
using namespace Core::Portable;
static std::uint32_t bits(float f) {
  std::uint32_t u;
  std::memcpy(&u, &f, 4);
  return u;
}
static float value(std::uint32_t u) {
  float f;
  std::memcpy(&f, &u, 4);
  return f;
}
static ParamInfo info(int tag, const char *name, int type = 3) {
  ParamInfo p{};
  p.type = type;
  p.tag = tag;
  std::strncpy(p.name, name, 31);
  p.minValue = -1.f;
  p.maxValue = 1.f;
  p.deltaValue = .01f;
  return p;
}
struct Observer : ParamObserverBase {
  std::vector<int> messages;
  void paramChanged(Parameter *, int m) override { messages.push_back(m); }
};
struct Env {
  Presonus::Mixer::MixerComponentBase mixer;
  presonus::panel_binding::PanelRegistrarPortState rs;
  PanelRegistrar registrar{rs};
  Component settings{"settings"}, scene{"scene"};
  presonus::frontpanel_port::State fs{settings};
  presonus::frontpanel_port::CheckedDependencies required;
  FrontPanelComponent front{fs, required};
  Env() {
    front.portableState().mixer = &mixer;
    front.portableState().registrar = &registrar;
    mixer.sceneSettings = &scene;
  }
};
static std::vector<std::string> split(std::string s, char sep) {
  std::vector<std::string> v;
  std::istringstream is(s);
  while (std::getline(is, s, sep))
    v.push_back(s);
  return v;
}
static void messages(const Observer &o) {
  std::cout << '[';
  for (int i : o.messages)
    std::cout << i << ',';
  std::cout << ']';
}
static void fader(std::string mode, int shape, int index, std::uint32_t input,
                  const std::vector<std::string> &ops) {
  Env env;
  Core::Vector<Presonus::Mixer::ChannelComponent *> bank, main;
  std::array<presonus::mixer::ChannelState, 5> states{};
  std::array<ParamInfo, 5> pi;
  std::array<Observer, 5> obs;
  std::vector<std::unique_ptr<NumericParam>> params;
  std::vector<std::unique_ptr<Presonus::Mixer::ChannelComponent>> channels;
  for (int i = 0; i < 5; ++i) {
    pi[i] = info(100 + i, ("locate" + std::to_string(i)).c_str());
    params.emplace_back(new NumericParam(pi[i]));
    params.back()->addObserver(&obs[i]);
    states[i].locatePosition =
        (shape == 3 && i == 2) ? nullptr : params.back().get();
    states[i].level = params[0].get();
    channels.emplace_back(new Presonus::Mixer::ChannelComponent(
        Presonus::Mixer::ChannelComponent::SourcePortConstruction{},
        states[i]));
  }
  if (shape == 1) {
    env.mixer.inputChannels.add(channels[0].get());
    bank.add(channels[1].get());
    main.add(channels[2].get());
  }
  if (shape >= 2) {
    for (int i = 0; i < 32; ++i)
      env.mixer.inputChannels.add(i % 7 == 0 ? nullptr : channels[i % 5].get());
    for (int i = 0; i < 7; ++i)
      bank.add(i == 1 ? nullptr : channels[(i + 1) % 5].get());
    main.add(channels[4].get());
    main.add(channels[0].get());
  }
  {
    Presonus::Mixer::MixerComponentBase other;
    bool rejected = false;
    try {
      env.front.bindFaderViews(other, bank, main);
    } catch (const std::logic_error &) {
      rejected = true;
    }
    assert(rejected);
    rejected = false;
    try {
      env.front.bindFaderViews(env.mixer, bank, bank);
    } catch (const std::logic_error &) {
      rejected = true;
    }
    assert(rejected);
  }
  env.front.bindFaderViews(env.mixer, bank, main);
  auto id = [&](auto *c) {
    for (int i = 0; i < 5; ++i)
      if (channels[i].get() == c)
        return i + 1;
    return 0;
  };
  if (mode == "describe") {
    auto list = [&](auto &v) {
      std::cout << '[';
      for (int i = 0; i < v.count(); ++i) {
        if (i)
          std::cout << ',';
        std::cout << id(v.at(i));
      }
      std::cout << ']';
    };
    std::cout << "{\"input\":";
    list(env.mixer.inputChannels);
    std::cout << ",\"bank\":";
    list(bank);
    std::cout << ",\"main\":";
    list(main);
    std::cout << ",\"locate\":[";
    for (int i = 0; i < 5; ++i) {
      if (i)
        std::cout << ',';
      std::cout << (states[i].locatePosition != nullptr);
    }
    std::cout << "]}\n";
    return;
  }
  if (mode == "application")
    env.front.faderPositionChanged(index, value(input));
  else
    for (auto &op : ops) {
      auto t = split(op, ':');
      assert(t[0] == "numeric" && t.size() == 4);
      params.at(std::stoi(t[1]) - 1)
          ->setValue(value(std::stoul(t[2])), std::stoi(t[3]) != 0);
    }
  for (int i = 0; i < 5; ++i) {
    std::cout << bits(params[i]->getValue());
    messages(obs[i]);
    std::cout << ' ';
    params[i]->removeObserver(&obs[i]);
  }
  std::cout << '\n';
}
static void meter(std::string mode, bool led, int kind, bool present,
                  int oldMode, int argument,
                  const std::vector<std::string> &ops) {
  Env env;
  int tag = led ? 12 : argument;
  auto targetInfo = info(tag, "target"), oldInfo = info(998, "old");
  NumericParam old(oldInfo);
  env.front.portableState().component.addParameters(&targetInfo,
                                                    present ? 1 : 0, false);
  auto *target = env.front.portableState().component.getParameterByTag(tag);
  // A decoy collection must never supply a missing PanelCore parameter.
  env.settings.addParameters(&targetInfo, 1, false);
  env.fs.panelParameters = &env.settings;
  Control base(3);
  LEDControl wrong(4, 1, 7);
  SwitchControl sw(5, 1, false);
  Control *control = kind == 0   ? nullptr
                     : kind == 1 ? &base
                     : kind == 2 ? static_cast<Control *>(&wrong)
                                 : static_cast<Control *>(&sw);
  if (control)
    control->setParameter(oldMode == 1   ? target
                          : oldMode == 2 ? &old
                                         : nullptr,
                          0);
  presonus::surface_panel_port::ledDispatchState().dirty.removeAll();
  presonus::surface_panel_port::ledDispatchState().disabled = 1;
  if (mode == "describe") {
    std::cout << "{\"cast\":"
              << (control && control->castTo(0x53776943) ? 1 : 0)
              << ",\"lookup\":" << (target ? 1 : 0) << "}\n";
  } else {
    if (mode == "application") {
      if (led)
        env.front.attachMeterTypeLed(control, argument);
      else
        env.front.attachMeterSwitch(control, argument);
    } else
      for (auto &op : ops) {
        auto t = split(op, ':');
        if (t[0] == "match")
          sw.setmatchvalue(std::stoi(t[1]));
        else if (t[0] == "set")
          sw.setParameter(std::stoi(t[1]) ? target : nullptr, std::stoi(t[2]));
        else if (t[0] == "lookup") {
          assert(env.front.portableState().component.getParameterByTag(
                     std::stoi(t[1])) == target);
        } else
          assert(t[0] == "cast");
      }
    auto state = [&]() {
      auto *p = control ? control->getParameter() : nullptr;
      std::cout << (p == nullptr  ? 0
                    : p == target ? 1
                    : p == &old   ? 2
                                  : 3)
                << ' ';
      for (auto x : presonus::surface_panel_port::LEDStateAccess::state(
               kind == 2 ? wrong : static_cast<LEDControl &>(sw)))
        std::cout << x << ',';
      std::cout
          << " dirty="
          << presonus::surface_panel_port::ledDispatchState().dirty.count()
          << '\n';
    };
    state();
    old.setValue(1.f, false);
    state();
    if (target)
      target->setValue(1.f, false);
    state();
  }
  presonus::surface_panel_port::ledDispatchState().dirty.removeAll();
  presonus::surface_panel_port::ledDispatchState().disabled = 0;
}
static void predicate(std::string mode, int key, int object, int controller,
                      int tag) {
  Env env;
  ParamInfo pinfo = info(tag, "predicate");
  NumericParam p(pinfo);
  Presonus::Mixer::ChannelComponent channel(
      Presonus::Mixer::ChannelComponent::SourcePortConstruction{});
  if (controller == 1)
    p.setController(&env.settings);
  if (controller == 2)
    p.setController(&channel);
  if (mode == "describe") {
    std::cout
        << "{\"controller\":" << (p.getController() ? 1 : 0) << ",\"cast\":"
        << (core_cast<Presonus::Mixer::ChannelComponent>(p.getController()) ? 1
                                                                            : 0)
        << ",\"tag\":" << p.getTag() << "}\n";
    return;
  }
  const FrontPanelComponent::CopyPasteFilter filter(
      FrontPanelComponent::CopyPasteFilter::SourcePortConstruction{});
  void *obj = object == 0   ? nullptr
              : object == 1 ? static_cast<void *>(&p)
                            : reinterpret_cast<void *>(1);
  std::cout << filter.shouldSave(key, reinterpret_cast<const char *>(1), obj)
            << '\n';
}
static void init(std::string mode, int number, bool present,
                 const std::vector<std::string> &ops) {
  Env env;
  env.rs.descriptionNumber = number;
  env.mixer.selectedChannel = 123456;
  auto pinfo = info(0, "description", ParamInfo::kString);
  env.scene.addParameters(&pinfo, present ? 1 : 0, false);
  auto *p = env.scene.getParameterByTag(0);
  if (p)
    p->fromString("previous", false);
  Observer observer;
  if (p)
    p->addObserver(&observer);
  if (mode == "describe") {
    std::cout << "{\"lookup\":" << (p ? 1 : 0)
              << ",\"number\":" << env.registrar.sourcePortDescriptionNumber()
              << "}\n";
    return;
  }
  if (mode == "application")
    env.front.init();
  else
    for (auto &op : ops) {
      auto t = split(op, ':');
      if (t[0] == "text") {
        std::string text;
        for (std::size_t i = 0; i < t[1].size(); i += 2)
          text += static_cast<char>(std::stoi(t[1].substr(i, 2), nullptr, 16));
        p->fromString(text.c_str(), std::stoi(t[2]) != 0);
      } else if (t[0] == "lookup")
        assert(env.scene.getParameterByTag(std::stoi(t[1])) == p);
      else
        assert(t[0] == "format");
    }
  if (p) {
    const char *text = static_cast<StringParam *>(p)->getText();
    for (std::size_t i = 0; i <= std::strlen(text); ++i)
      std::cout << std::hex
                << static_cast<unsigned>(static_cast<unsigned char>(text[i]))
                << ',';
    messages(observer);
    p->removeObserver(&observer);
  } else
    std::cout << "absent";
  std::cout << '\n';
}
int main(int argc, char **argv) {
  assert(argc >= 3);
  std::string mode = argv[1], task = argv[2];
  if (mode == "format") {
    Core::CString64 text;
    text.appendFormat("%d", std::stoi(argv[2]));
    std::cout << static_cast<const char *>(text);
    return 0;
  }
  std::vector<std::string> ops;
  std::string token;
  while (std::cin >> token)
    ops.push_back(token);
  if (task == "fader") {
    assert(argc == 6);
    fader(mode, std::stoi(argv[3]), std::stoi(argv[4]), std::stoul(argv[5]),
          ops);
  }
  if (task == "led" || task == "switch") {
    assert(argc == 7);
    meter(mode, task == "led", std::stoi(argv[3]), std::stoi(argv[4]),
          std::stoi(argv[5]), std::stoi(argv[6]), ops);
  }
  if (task == "predicate") {
    assert(argc == 7);
    predicate(mode, std::stoi(argv[3]), std::stoi(argv[4]), std::stoi(argv[5]),
              std::stoi(argv[6]));
  }
  if (task == "init") {
    assert(argc == 5);
    init(mode, std::stoi(argv[3]), std::stoi(argv[4]), ops);
  }
}
