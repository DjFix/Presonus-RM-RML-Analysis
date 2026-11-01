#include "presonus/mixer/MasterSectionComponent.hpp"
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
using namespace Core::Portable;
namespace {
std::uint32_t bits(float f) {
  std::uint32_t b;
  std::memcpy(&b, &f, 4);
  return b;
}
std::string q(const std::string &s) {
  std::ostringstream o;
  o << std::quoted(s);
  return o.str();
}
std::vector<std::string> trace;
int offsets[16] = {140, 260, 264, 268, 272, 276, 280, 284,
                   288, 292, 296, 300, 304, 308, 312, 316};
std::string setEvent(int off, float v, bool edit) {
  return "[\"set\"," + std::to_string(off) + "," + std::to_string(bits(v)) +
         "," + (edit ? "true" : "false") + "]";
}
struct Numeric : NumericParam {
  float v = 0, n = 0;
  int off;
  Numeric(const ParamInfo &info, int off) : NumericParam(info), off(off) {}
  float getValue() const override { return v; }
  float getNormalized() const override { return n; }
  void setValue(float value, bool edit = false) override {
    v = value;
    NumericParam::value = value;
    trace.push_back(setEvent(off, v, edit));
  }
};
struct List : ListParam {
  float v = 0, n = 0;
  int off;
  bool suppress = false;
  List(const ParamInfo &info, int off) : ListParam(info), off(off) {}
  float getValue() const override { return v; }
  float getNormalized() const override { return n; }
  void setValue(float value, bool edit = false) override {
    v = value;
    NumericParam::value = value;
    if (!suppress)
      trace.push_back(setEvent(off, v, edit));
  }
  void fromString(const char *s, bool edit = false) override {
    suppress = true;
    ListParam::fromString(s, edit);
    suppress = false;
  }
};
struct TestComponent : Core::Portable::Component {
  void add(Parameter *p) { paramList.add(p); }
};
std::string property(const presonus::mixer_port::MasterProperty &p) {
  std::string out = "[";
  for (std::size_t i = 0; i < p.entries.size(); ++i) {
    if (i)
      out += ",";
    out += "[" + std::to_string(p.entries[i].index) + "," +
           std::to_string(bits(p.entries[i].value)) + "]";
  }
  return out + "]";
}
} // namespace
int main() {
  int target, slave, master, merge, blocked, expired, global, castFail, index,
      count;
  float newValue;
  int a0, a1, a2, s0, s4, sa;
  if (!(std::cin >> target >> slave >> master >> merge >> blocked >> expired >>
        global >> castFail >> index >> count >> newValue >> a0 >> a1 >> a2 >>
        s0 >> s4 >> sa))
    return 2;
  std::vector<int> missing;
  int nm;
  std::cin >> nm;
  for (int i = 0, v; i < nm; ++i) {
    std::cin >> v;
    missing.push_back(v);
  }
  TestComponent parameters, globalComponent;
  std::array<ParamInfo, 20> infos{};
  std::array<Parameter *, 16> slots{};
  std::vector<std::unique_ptr<Parameter>> owned;
  std::array<float, 16> initial{};
  std::array<List *, 16> lists{};
  std::array<Numeric *, 16> numerics{};
  for (int i = 0; i < 16; ++i) {
    float value, normalized;
    std::cin >> value >> normalized;
    initial[i] = value;
    auto &info = infos[i];
    info.type = ParamInfo::kFloat;
    info.tag = 100 + i;
    std::strcpy(info.name, "p");
    info.minValue = -100000;
    info.maxValue = 100000;
    int tag = (i == 11   ? 16
               : i == 12 ? 17
               : i == 13 ? 24
               : i == 14 ? 25
               : i == 15 ? 26
                         : -1);
    if (i >= 14) {
      info.type = ParamInfo::kList;
      auto p = std::make_unique<List>(info, offsets[i]);
      p->v = value;
      p->n = normalized;
      lists[i] = p.get();
      slots[i] = p.get();
      owned.push_back(std::move(p));
    } else {
      auto p = std::make_unique<Numeric>(info, offsets[i]);
      p->v = value;
      p->n = normalized;
      numerics[i] = p.get();
      slots[i] = p.get();
      owned.push_back(std::move(p));
    }
    if (tag >= 0 &&
        std::find(missing.begin(), missing.end(), tag) == missing.end()) {
      auto *p = slots[i];
      info.tag = tag;
      if (castFail && i >= 14) {
        auto &bad = infos[16 + i - 14];
        bad = info;
        bad.type = ParamInfo::kFloat;
        parameters.add(new Numeric(bad, offsets[i]));
      } else {
        parameters.add(p);
        owned.back().release();
      }
    }
  }
  for (int i = 0; i < 16; ++i) {
    int n;
    std::cin >> n;
    for (int j = 0; j < n; ++j) {
      std::string s;
      std::cin >> std::quoted(s);
      if (lists[i])
        lists[i]->appendString(s.c_str());
    }
  }
  for (int i = 0; i < 16; ++i)
    slots[i]->setValue(initial[i]);
  Presonus::DelayTimer timer(1.f);
  presonus::timing::DelayTimerAccess::set(
      timer, {0, 1000, expired ? 1000 : 0, 0, false});
  presonus::mixer_port::MasterBindings b{parameters, slots, timer};
  for (auto &v : b.cache)
    std::cin >> v;
  int nc;
  std::cin >> nc;
  std::vector<std::unique_ptr<Numeric>> channels;
  std::vector<ParamInfo> channelInfo(nc);
  for (int i = 0; i < nc; ++i) {
    int state;
    std::cin >> state;
    auto &info = channelInfo[i];
    info = infos[0];
    auto p = std::make_unique<Numeric>(info, 4096 + i);
    p->v = state;
    b.channels.push_back({state >= 0, state > 0 ? p.get() : nullptr});
    channels.push_back(std::move(p));
  }
  for (auto &s : b.labels)
    std::cin >> std::quoted(s);
  std::cin >> std::quoted(b.pairSeparator);
  b.populateRoutes = [&](ListParam &list) {
    trace.push_back("[\"route\"," +
                    std::to_string(&list == lists[14] ? 312 : 316) + "]");
  };
  b.countSolos = [&](int kind) {
    trace.push_back("[\"count\"," + std::to_string(kind) + "]");
    return kind == 0 ? s0 : kind == 4 ? s4 : sa;
  };
  b.isSlave = [&] {
    trace.push_back("[\"slave\"]");
    return slave;
  };
  b.isMaster = [&] {
    trace.push_back("[\"master\"]");
    return master;
  };
  b.isSubgroupMerge = [&] {
    trace.push_back("[\"merge\"]");
    return merge;
  };
  b.solosBlocked = [&] { return blocked; };
  b.clearSolos = [] { trace.push_back("[\"clear\"]"); };
  b.clearSIPSolos = [] { trace.push_back("[\"clearSIP\"]"); };
  b.targetedIdle = [] { trace.push_back("[\"idle\"]"); };
  b.slaveID = [] { return 7; };
  b.sendSolo = [](const Presonus::UC::MessageAttributes &message, int id,
                  int slaveID) {
    trace.push_back(
        "[\"event\",{\"name\":" + q(message.getID()) + ",\"InputSoloCount\":" +
        std::to_string(message.getInt("InputSoloCount")) +
        ",\"MixSoloCount\":" + std::to_string(message.getInt("MixSoloCount")) +
        "}," + std::to_string(id) + ",0]");
    trace.push_back("[\"send\"," + std::to_string(slaveID) + ",0]");
  };
  infos[18] = infos[0];
  infos[18].tag = 45;
  auto *globalValue = new Numeric(infos[18], 312);
  globalValue->v = slots[14]->getValue();
  globalComponent.add(globalValue);
  b.globalComponent = [&]() -> Core::Portable::Component * {
    return global ? &globalComponent : nullptr;
  };
  b.submitProperty = [](const auto &p) {
    trace.push_back("[\"property\"," + property(p) + "]");
  };
  presonus::mixer_port::MasterProperty prop;
  prop.count = count;
  prop.entries.resize(count);
  b.property = [&](Presonus::Dsp::MultiParamProperty &) -> auto & {
    return prop;
  };
  Presonus::Mixer::MasterSectionComponent object(b);
  trace.clear();
  switch (target) {
  case 1:
    object.populateRouteList(25);
    break;
  case 2:
    object.localSoloChanged();
    break;
  case 3:
    object.remoteSoloChanged(a0, a1, a2);
    break;
  case 4:
    object.buildRemoteMonitorSelectList();
    break;
  case 5:
    object.onMonitorSelectChanged();
    break;
  case 6:
    object.rebuildMonitorSelectList();
    break;
  case 7: {
    alignas(16) unsigned char opaque[16]{};
    object.addControlRmProperty(
        *reinterpret_cast<Presonus::Dsp::MultiParamProperty *>(opaque), index,
        newValue);
    break;
  }
  case 8:
    object.doUpdates();
    break;
  case 9:
    object.onIdle();
    break;
  case 10:
    object.updateControlRoom();
    break;
  default:
    return 3;
  }
  std::cout << "{\"trace\":[";
  for (std::size_t i = 0; i < trace.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << trace[i];
  }
  std::cout << "],\"dirty\":" << int(b.dirty) << ",\"cache\":[";
  for (int i = 0; i < 13; ++i) {
    if (i)
      std::cout << ',';
    std::cout << bits(b.cache[i]);
  }
  std::cout << "],\"values\":{";
  for (int i = 0; i < 16; ++i) {
    if (i)
      std::cout << ',';
    std::cout << q(std::to_string(offsets[i])) << ':'
              << bits(slots[i]->getValue());
  }
  std::cout << "},\"lists\":{";
  for (int i = 0; i < 16; ++i) {
    if (i)
      std::cout << ',';
    std::cout << q(std::to_string(offsets[i])) << ":[";
    if (lists[i])
      for (int j = 0; j < lists[i]->getStringCount(); ++j) {
        if (j)
          std::cout << ',';
        std::cout << q(lists[i]->getStringAt(j));
      }
    std::cout << ']';
  }
  std::cout << "},\"property_count\":" << prop.count;
  if (target == 7)
    std::cout << ",\"property\":" << property(prop);
  std::cout << "}\n";
}
