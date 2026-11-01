#include "presonus/panel/GeqUIComponent.hpp"
#include <array>
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <vector>
using namespace Core::Portable;
using Presonus::Mixer::ChannelComponent;
using Presonus::Mixer::GEQComponent;
namespace {
std::ostringstream events;
std::uint32_t bits(float f) {
  std::uint32_t x;
  std::memcpy(&x, &f, 4);
  return x;
}
ParamInfo info(int tag, int type = ParamInfo::kFloat) {
  ParamInfo p{};
  p.type = type;
  p.tag = tag;
  p.minValue = -1e10f;
  p.maxValue = 1e10f;
  return p;
}
struct TracedParam : NumericParam {
  using NumericParam::signal;
  int component;
  bool enabled = true;
  bool capture = false;
  TracedParam(const ParamInfo &i, int c) : NumericParam(i), component(c) {}
  void setValue(float f, bool edit = false) override {
    if (capture)
      events << "s:" << component << ":" << getTag() << ":" << bits(f) << ":"
             << edit << ";";
    NumericParam::setValue(f, edit);
  }
  void enable(bool b) override {
    enabled = b;
    if (capture)
      events << "e:" << component << ":" << getTag() << ":" << b << ";";
    Parameter::enable(b);
  }
};
struct Parameters : Component {
  void add(Parameter *p) { paramList.add(p); }
};
struct UI : Presonus::Panel::GeqUIComponent {
  using GeqUIComponent::GeqUIComponent;
  void add(Parameter *p) { paramList.add(p); }
  void paramChanged(Parameter *p, int msg) override {
    if (msg == 99)
      events << "w:" << p->getTag() << ";";
    else
      GeqUIComponent::paramChanged(p, msg);
  }
};
struct Controller : ParamObserverBase {
  void paramChanged(Parameter *, int) override {}
};
struct Boundary : presonus::gequi_port::Dependencies {
  std::array<Parameters, 5> params;
  int present, kind, index, ctrl;
  bool channelPresent, linkedFlag, slave, update;
  TracedParam &stereo;
  Controller controller;
  Boundary(int present, int kind, int index, int ctrl, bool cp, bool l, bool s,
           bool u, TracedParam &stereo)
      : present(present), kind(kind), index(index), ctrl(ctrl),
        channelPresent(cp), linkedFlag(l), slave(s), update(u), stereo(stereo) {
  }
  static GEQComponent *g(int i) {
    return reinterpret_cast<GEQComponent *>(static_cast<std::uintptr_t>(i + 1));
  }
  static ChannelComponent *c() {
    return reinterpret_cast<ChannelComponent *>(std::uintptr_t(100));
  }
  static int gi(GEQComponent *p) {
    return int(reinterpret_cast<std::uintptr_t>(p)) - 1;
  }
  int geqCount() const override { return 4; }
  GEQComponent *geqAt(int i) const override {
    return present & (1 << i) ? g(i) : nullptr;
  }
  Component &parameters(GEQComponent *p) override { return params[gi(p)]; }
  Component &parameters(ChannelComponent *) override { return params[4]; }
  int channelKind(ChannelComponent *) const override { return kind; }
  std::uint32_t channelIndex(ChannelComponent *) const override {
    return static_cast<std::uint32_t>(index);
  }
  Parameter &channelLink(ChannelComponent *) override { return stereo; }
  ChannelComponent *assignedChannel(int) override {
    return channelPresent ? c() : nullptr;
  }
  bool linked(GEQComponent *) const override { return linkedFlag; }
  bool linkSlave(GEQComponent *) const override { return slave; }
  bool linked(ChannelComponent *) const override { return linkedFlag; }
  void flatten(GEQComponent *p) override { events << "f:" << gi(p) << ";"; }
  GEQComponent *geqController(IParamObserver *p) override {
    return p && ctrl == 1 ? g(0) : nullptr;
  }
  ChannelComponent *channelController(IParamObserver *p) override {
    return p && ctrl == 2 ? c() : nullptr;
  }
  bool channelUpdateLink(ChannelComponent *) const override { return update; }
  void updateGeqNameList() override { events << "n;"; }
};
} // namespace
int main(int argc, char **argv) {
  if (argc != 21)
    return 2;
  std::array<int, 20> a{};
  for (int i = 0; i < 20; ++i)
    a[i] = std::atoi(argv[i + 1]);
  // Floats are supplied as IEEE754 integer words for exact transport.
  auto fl = [&](int i) {
    std::uint32_t u = std::strtoul(argv[i + 1], nullptr, 10);
    float f;
    std::memcpy(&f, &u, 4);
    return f;
  };
  auto si = info(99);
  TracedParam stereo(si, 4);
  stereo.setValue(fl(8));
  std::vector<std::unique_ptr<ParamInfo>> infos;
  Boundary b(a[4], a[6], a[7], a[14], a[5], a[15], a[16], a[11], stereo);
  UI ui(b);
  ui.configureSelection(a[1], a[2]);
  std::array<std::array<TracedParam *, 33>, 5> ps{};
  for (int c = 0; c < 5; ++c)
    for (int t = 0; t < 33; ++t) {
      if (c < 4 && t == a[18])
        continue;
      if (c == 4 && t != 22)
        continue;
      auto inf = std::make_unique<ParamInfo>(info(t));
      auto *p = new TracedParam(*inf, c);
      p->setValue(c == 4 ? fl(9) : (t == 32 ? fl(10) : 0.f));
      ps[c][t] = p;
      b.params[c].add(p);
      infos.push_back(std::move(inf));
    }
  static auto p1info = info(1), p5info = info(5),
              p2info = info(2, ParamInfo::kAlias);
  auto *p1 = new TracedParam(p1info, -1);
  p1->setValue(fl(17));
  ui.add(p1);
  Parameter *alias = nullptr;
  if (a[12] == 1)
    alias = new AliasParam(p2info);
  else if (a[12] == 2)
    alias = new TracedParam(p2info, -1);
  if (alias)
    ui.add(alias);
  TracedParam *p5 = nullptr;
  if (!a[19]) {
    p5 = new TracedParam(p5info, -1);
    ui.add(p5);
  }
  auto changedInfo = info(a[13]);
  TracedParam changed(changedInfo, 4);
  if (a[14])
    changed.setController(&b.controller);
  if (a[0] == 5 && !a[11])
    for (int t = 0; t < 32; ++t)
      if (ps[0][t])
        ps[0][t]->addObserver(&ui);
  if (a[0] == 9 && a[3] == 5)
    changed.addObserver(&ui);
  p1->capture = true;
  if (p5)
    p5->capture = true;
  for (auto &row : ps)
    for (auto *p : row)
      if (p)
        p->capture = true;
  int ret = -9;
  switch (a[0]) {
  case 1:
    ui.updateStereoLink(a[5] ? Boundary::c() : nullptr, a[11]);
    break;
  case 2:
    ret = ui.isChildParameter(
        a[3] == 0 ? *p1 : (a[3] == 1 && alias ? *alias : changed));
    break;
  case 3:
    ret = ui.isChannelLinked(static_cast<unsigned>(a[3]));
    break;
  case 4:
    ui.flattenCurrentGeq();
    break;
  case 5:
    ui.addRemoveWatchers(a[3], a[11]);
    for (int t = 0; t < 32; ++t)
      if (ps[0][t])
        ps[0][t]->signal(99);
    break;
  case 6:
    ui.selectBand(a[3]);
    break;
  case 7:
    ui.updateBandSelect();
    break;
  case 8: {
    auto *p = ui.getGeqForChannel(a[5] ? Boundary::c() : nullptr);
    ret = p ? Boundary::gi(p) : -1;
    break;
  }
  case 9:
    ui.observedParamChanged(a[5] ? &changed : nullptr, a[3]);
    break;
  case 10:
    ui.updateStereoField();
    break;
  default:
    return 3;
  }
  int original = -1;
  if (auto *p = Core::Portable::core_cast<AliasParam>(alias))
    if (auto *q = p->getOriginal())
      original = q->getTag();
  std::cout << ret << "|" << ui.selectedBand() << "|" << original << "|"
            << events.str() << "|" << bits(p1->getValue()) << "|";
  if (p5)
    std::cout << bits(p5->getValue());
  else
    std::cout << -1;
  for (int c = 0; c < 4; ++c) {
    std::cout << "|";
    if (ps[c][32])
      std::cout << bits(ps[c][32]->getValue()) << ":" << ps[c][32]->enabled;
    else
      std::cout << -1;
  }
  std::cout << "\n";
  // Detach borrowed UI observers before the dependent components are destroyed.
  for (auto &row : ps)
    for (auto *p : row)
      if (p)
        p->removeObserver(&ui);
}
