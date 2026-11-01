#include "presonus/mixer/InputComponent.hpp"
#include <cstring>
#include <iostream>
#include <memory>
#include <vector>
using namespace presonus::input_port;
namespace {
std::uint32_t bits(float v) {
  std::uint32_t b;
  std::memcpy(&b, &v, 4);
  return b;
}
float value(std::uint32_t b) {
  float v;
  std::memcpy(&v, &b, 4);
  return v;
}
const Core::Portable::ParamInfo roleInfo =
    PARAM_FLOAT(0, "role", 0, 1, 0, 1, nullptr, nullptr, 0, 0);
struct Boundary : Providers {
  Property *property = nullptr;
  Core::Portable::Parameter *prepost = nullptr;
  std::vector<std::uint32_t> effects;
  Property &resolveProperty(const void *) override { return *property; }
  Core::Portable::Parameter *auxPrePost(Core::Portable::Component &) override {
    return prepost;
  }
  void channelSectionChanged(int section) override {
    effects.insert(effects.end(), {1, static_cast<std::uint32_t>(section)});
  }
  void channelUpdates() override { effects.push_back(2); }
  void meterLevel(int channel, float level) override {
    effects.insert(effects.end(),
                   {3, 1836278636u, 20, static_cast<std::uint32_t>(channel), 0,
                    bits(level)});
  }
  void update(int slot, Property &) override {
    effects.insert(effects.end(), {4, static_cast<std::uint32_t>(slot)});
  }
  void submit(const Property &p) override {
    effects.insert(effects.end(),
                   {5, static_cast<std::uint32_t>(3 + 2 * p.count), p.id,
                    static_cast<std::uint32_t>(p.channel),
                    static_cast<std::uint32_t>(p.count)});
    for (int i = 0; i < p.count; ++i)
      effects.insert(
          effects.end(),
          {static_cast<std::uint32_t>(p.entries[i].tag), p.entries[i].value});
  }
};
void add(Core::Portable::Component &c, const Core::Portable::ParamInfo &info,
         float v) {
  c.addParameters(&info, 1);
  static_cast<Core::Portable::NumericParam *>(c.getParameterByTag(info.tag))
      ->setValueFast(v);
}
} // namespace
int main() {
  int method, arg, count, mask, lookup, auxCount, subCount, subPresent, subLink,
      slave, cachedComponent, cachedParam;
  while (std::cin >> method >> arg >> count >> mask >> lookup >> auxCount >>
         subCount >> subPresent >> subLink >> slave >> cachedComponent >>
         cachedParam) {
    std::array<std::uint32_t, 16> params{};
    for (auto &p : params)
      std::cin >> p;
    std::array<std::uint32_t, 9> scalars{};
    for (auto &p : scalars)
      std::cin >> p;
    std::array<std::uint32_t, 23> initial{};
    for (auto &p : initial)
      std::cin >> p;
    State s;
    std::vector<std::unique_ptr<Core::Portable::NumericParam>> roles;
    for (auto p : params) {
      roles.push_back(std::make_unique<Core::Portable::NumericParam>(roleInfo));
      roles.back()->setValueFast(value(p));
    }
    for (int i = 0; i < 10; ++i)
      s.parametersByRole[i] = (mask >> i & 1) ? roles[i].get() : nullptr;
    const Core::Portable::ParamInfo subInfo =
        PARAM_FLOAT(411, "subgroup", -100, 100, 0, 1, nullptr, nullptr, 0, 0);
    const Core::Portable::ParamInfo globalInfo =
        PARAM_FLOAT(28, "mute", -100, 100, 0, 1, nullptr, nullptr, 0, 0);
    const Core::Portable::ParamInfo assignedInfo =
        PARAM_FLOAT(static_cast<int>(static_cast<std::uint32_t>(arg) + 256u),
                    "assigned", -100, 100, 0, 1, nullptr, nullptr, 0, 0);
    Core::Portable::Component component, auxiliary, global;
    if (lookup & 2)
      add(auxiliary, subInfo, value(params[11]));
    if (lookup & 4)
      add(component, assignedInfo, value(params[12]));
    if (lookup & 8)
      add(global, globalInfo, value(params[13]));
    s.parameters = &component;
    s.globalComponent = &global;
    s.auxError = &auxiliary;
    GlobalMuteCache cache{cachedComponent ? &global : nullptr,
                          cachedParam ? roles[13].get() : nullptr};
    s.globalCache = &cache;
    for (int i = 0; i < auxCount; ++i)
      s.auxiliaries.push_back(&auxiliary);
    std::array<Subgroup, 8> groups{};
    for (int i = 0; i < subCount; ++i) {
      groups[i].linked = (subLink >> i & 1) ? roles[14].get() : nullptr;
      groups[i].slave = slave >> i & 1;
      s.subgroups.push_back((subPresent >> i & 1) ? &groups[i] : nullptr);
    }
    for (int i = 0; i < 7; ++i)
      s.levels[i] = value(scalars[i]);
    s.channelType = static_cast<int>(scalars[7]);
    s.channelIndex = static_cast<int>(scalars[8]);
    for (int i = 0; i < 6; ++i)
      s.changed[i] = static_cast<int>(initial[i]);
    for (int i = 0; i < 13; ++i)
      s.cachedLevels[i] = value(initial[i + 6]);
    for (int i = 0; i < 4; ++i)
      s.cachedIntegers[i] = static_cast<int>(initial[i + 19]);
    Boundary boundary;
    Property property;
    property.count = count;
    boundary.property = &property;
    boundary.prepost = (lookup & 1) ? roles[10].get() : nullptr;
    Presonus::Mixer::InputComponent target(s, boundary);
    bool result = false;
    auto &f = *reinterpret_cast<Presonus::Dsp::MultiParamProperty *>(&property);
    auto &n =
        *reinterpret_cast<Presonus::Dsp::MultiParamIntProperty *>(&property);
    switch (method) {
    case 1:
      target.assignSubsUpdate(f);
      break;
    case 2:
      result = target.isPostFaderAux(arg);
      break;
    case 3:
      result = target.isSubgroupModeAux(arg);
      break;
    case 4:
      target.assignLRUpdate(f);
      break;
    case 5:
      result = target.isGlobalAuxMute();
      break;
    case 6:
      target.setSectionCoeffChanged(arg);
      break;
    case 7:
      target.soloUpdate(f);
      break;
    case 8:
      target.linkUpdate(n);
      break;
    case 9:
      target.doUpdates();
      break;
    case 10:
      result = target.auxAssigned(arg);
      break;
    default:
      return 2;
    }
    for (auto p : s.changed)
      std::cout << static_cast<std::uint32_t>(p) << ' ';
    for (auto p : s.cachedLevels)
      std::cout << bits(p) << ' ';
    for (auto p : s.cachedIntegers)
      std::cout << static_cast<std::uint32_t>(p) << ' ';
    std::cout << property.count << ' ';
    for (int i = count; i < property.count; ++i)
      std::cout << property.entries[i].tag << ' ' << property.entries[i].value
                << ' ';
    std::cout << boundary.effects.size() << ' ';
    for (auto p : boundary.effects)
      std::cout << p << ' ';
    if (method == 2 || method == 3 || method == 5 || method == 10)
      std::cout << result;
    std::cout << '\n';
  }
}
