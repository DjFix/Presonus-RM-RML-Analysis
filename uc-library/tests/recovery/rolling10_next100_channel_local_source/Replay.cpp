#define CASE 4
#include "presonus/panel/AlertBook.hpp"
#include "presonus/surface/ChannelInfoPageComponent.hpp"
#include "presonus/surface/MixSettingsPageComponent.hpp"
#include "presonus/surface/MonitorPageComponent.hpp"
#include "presonus/surface/SurfaceInputComponent.hpp"
#if CASE == 2
#include "presonus/mixer/RackMixerComponent.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#endif
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <vector>
using namespace Core::Portable;
float f(unsigned x) {
  float y;
  std::memcpy(&y, &x, 4);
  return y;
}
unsigned bits(float x) {
  unsigned y;
  std::memcpy(&y, &x, 4);
  return y;
}
std::string hex(const std::string &s) {
  std::string out;
  const char *d = "0123456789abcdef";
  for (unsigned char c : s) {
    out += d[c >> 4];
    out += d[c & 15];
  }
  return out.empty() ? "-" : out;
}
std::string unhex(std::string s) {
  if (s == "-")
    return {};
  std::string out;
  for (unsigned i = 0; i < s.size(); i += 2)
    out += char(std::stoul(s.substr(i, 2), nullptr, 16));
  return out;
}
struct Observer : ParamObserverBase {
  std::vector<int> events;
  void paramChanged(Parameter *p, int msg) override {
    events.push_back(p->getTag());
    events.push_back(msg);
  }
};
#if CASE == 2
// This argument is unused by the target. Trap every service rather than supply
// any fabricated registrar behavior.
struct Registrar : Presonus::Panel::ControlRegistrar {
  void writeDualMsg(Uart_Msg_Type &) override { std::abort(); }
  void setAllLeds(bool) override { std::abort(); }
  void setAllMeters(bool) override { std::abort(); }
  void scanSurface() override { std::abort(); }
};
#endif
int main(int argc, char **argv) {
  unsigned mask, a, b, mode, msg, stop, type;
  std::string textHex;
  if (!(std::cin >> mask >> a >> b >> mode >> msg >> stop >> type >> textHex))
    return 2;
  bool provider = argc > 1 && std::string(argv[1]) == "--provider";
  std::string text = unhex(textHex);
  Observer observer;
  std::vector<std::unique_ptr<ParamInfo>> infos;
  std::vector<Parameter *> params;
  Component ordinary("registry");
  Component *registry = &ordinary;
#if CASE == 3
  Presonus::Surface::MixSettingsPageComponent target("mix");
  registry = &target;
#elif CASE == 4 || CASE == 5
  Presonus::Surface::ChannelInfoPageComponent target("channel");
  registry = &target;
#elif CASE == 7
  Presonus::Surface::SurfaceInputComponent target;
  registry = &target;
  target.channelMode = mode;
#elif CASE == 2
  Presonus::Mixer::MixerComponentBase base;
  std::uint32_t cascade = 0;
  Presonus::Mixer::RackMixerComponent target(base, cascade);
  Registrar registrar;
  Presonus::Mixer::ChannelComponent channel(
      Presonus::Mixer::ChannelComponent::SourcePortConstruction{});
  registry = &channel;
  base.hardwareMicLineInputs = mode;
  if (mask)
    base.inputChannels.add(mask == 1 ? nullptr : &channel);
#endif
  auto add = [&](int tag, const char *name, bool string, float value,
                 const char *title = "Title", float maximum = 10000.f) {
    auto info = std::make_unique<ParamInfo>();
    *info = {};
    info->tag = tag;
    std::strncpy(info->name, name, 31);
    info->type = string ? ParamInfo::kString : ParamInfo::kFloat;
    info->minValue = -10000.f;
    info->maxValue = maximum;
    info->defaultValue = 0;
    info->title = title;
    auto *p = registry->getParameterByTag(tag);
    if (p)
      std::abort();
    registry->addParameters(info.get(), 1);
    p = registry->getParameterByTag(tag);
    if (!string)
      p->setValue(value, false);
    p->addObserver(&observer);
    params.push_back(p);
    infos.push_back(std::move(info));
    return p;
  };
#if CASE == 1
  if (mask)
    add(17, "alert", mask == 2, 7.f);
  Presonus::Panel::AlertBook target(*registry);
#elif CASE == 2
  if (mask == 3)
    add(313, "linesense", false, 7.f);
#elif CASE == 3
  add(17, type ? "busdelay" : "other", false, 0.f, "Source", f(a));
  add(1000, "destination", false, 7.f);
#elif CASE == 4 || CASE == 5
  if (mask & 1)
    add(17, "dig_in", false, f(a));
  if (mask & 2)
    add(18, "dig_opt", false, f(b));
  add(1009, "destination", false, 7.f);
#elif CASE == 6
  for (unsigned tag = 101; tag <= stop; ++tag)
    if (tag == stop || !(type && tag == 102))
      add(tag, "selection", false, tag == stop ? f(a) : 0.f, "SelectedTitle");
  if (mask)
    add(19, "monitorlist", true, 0.f);
  Presonus::Surface::MonitorPageComponent target(
      Presonus::Surface::MonitorPageComponent::SourcePortConstruction{},
      *registry);
#elif CASE == 7
  if (mask)
    add(301, "pot", false, 7.f, "Pot", 255.f);
#endif
  observer.events.clear();
  unsigned result = 0;
  auto pointer = [&](Parameter *p) {
    if (!p)
      return 0u;
    for (unsigned i = 0; i < params.size(); ++i)
      if (params[i] == p)
        return 0x1100000u + i * 4096u;
    std::abort();
  };
  auto param = [&](unsigned address) {
    unsigned i = (address - 0x1100000u) / 4096u;
    if (i >= params.size())
      std::abort();
    return params[i];
  };
  auto report = [&]() {
    std::cout << result;
    for (auto *p : params) {
      std::cout << ' ' << p->getTag() << ':' << bits(p->getValue()) << ':';
      if (auto *sp = StringParam::cast(p)) {
        char data[512];
        sp->toString(data, sizeof(data));
        std::cout << hex(data);
      } else
        std::cout << '-';
    }
    std::cout << " E";
    for (int x : observer.events)
      std::cout << ':' << x;
    std::cout << std::endl;
  };
  if (!provider) {
#if CASE == 1
    target.setParamString(text.c_str(), 17);
#elif CASE == 2
    target.lineSenseChanged(registrar, static_cast<int>(a),
                            static_cast<int>(b));
#elif CASE == 3
    target.paramChanged(params[0], static_cast<int>(msg));
#elif CASE == 4
    target.handleLocalSourceSelect(f(a));
#elif CASE == 5
    target.handleExternalSourceSelect();
#elif CASE == 6
    target.applyMonitorSelection();
    if (target.monitorSelectionInProgress())
      return 5;
#elif CASE == 7
    result = target.setLevel(f(a));
#endif
    report();
    return 0;
  }
  std::string op;
  while (std::cin >> op) {
    unsigned x = 0, y = 0, z = 0;
    int out = 0;
    if (op == "TAG") {
      std::cin >> x;
      out = pointer(registry->getParameterByTag(static_cast<int>(x)));
    } else if (op == "FIND") {
      std::string n;
      std::cin >> n;
      out = pointer(registry->findParameter(unhex(n).c_str()));
    } else if (op == "VAL") {
      std::cin >> x;
      out = bits(param(x)->getValue());
    } else if (op == "MAX") {
      std::cin >> x;
      out = bits(param(x)->getMax());
    } else if (op == "SET") {
      std::cin >> x >> y >> z;
      param(x)->setValue(f(y), z);
    } else if (op == "CAST") {
      std::cin >> x;
      out = pointer(StringParam::cast(param(x)));
    } else if (op == "STR") {
      std::string h;
      std::cin >> x >> h >> z;
      param(x)->fromString(unhex(h).c_str(), z);
    } else if (op == "NAME") {
      std::cin >> x;
      std::cout << hex(param(x)->getName()) << std::endl;
      continue;
    } else if (op == "TITLE") {
      std::cin >> x;
      std::cout << hex(param(x)->getTitle(false)) << std::endl;
      continue;
    } else if (op == "BASE") {
      std::cin >> x >> y;
      registry->Component::paramChanged(param(x), static_cast<int>(y));
    } else if (op == "HW") {
#if CASE == 2
      out = base.numHWMicLineIn();
#else
      return 6;
#endif
    } else if (op == "RETURN") {
      std::cin >> result;
    } else if (op == "REPORT") {
      report();
      continue;
    } else
      return 7;
    std::cout << static_cast<unsigned>(out) << std::endl;
  }
}
