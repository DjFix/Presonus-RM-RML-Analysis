#include "presonus/mixer_dsp/EQControl.hpp"
#include <array>
#include <iostream>
#include <memory>
#include <vector>
using P = Core::Portable::Parameter;
using EQ = Presonus::EQControl;
using BP = EQ::BandParams;
struct Parameter : Core::Portable::NumericParam {
  using NumericParam::NumericParam;
  int members() const { return observerList.count(); }
};
static std::vector<std::vector<int>> trace;
static std::vector<P *> pool;
static EQ *owner;
static bool recording;
static int selected;
static std::array<int, 6> raw(const BP &b) {
  auto id = [](P *p) {
    if (!p)
      return 0;
    for (unsigned i = 0; i < pool.size(); ++i)
      if (pool[i] == p)
        return static_cast<int>(i + 1);
    std::abort();
  };
  return {id(b.slot3),     id(b.gain),  id(b.q),
          id(b.frequency), id(b.slot4), id(b.slot5)};
}
static void observe(int kind, P *p, Core::Portable::IParamObserver *o) {
  if (!recording)
    return;
  int id = 0;
  for (unsigned i = 0; i < pool.size(); ++i)
    if (pool[i] == p)
      id = i + 1;
  if (!id || (o && o != owner->portableObserver()))
    std::abort();
  std::vector<int> row{kind, id, o ? 1 : 0};
  if (selected >= 0 &&
      selected < static_cast<int>(owner->portableBandState().size())) {
    for (int value : raw(owner->portableParameterState()[selected]))
      row.push_back(value);
    row.push_back(owner->portableBandState()[selected].dirty);
  }
  trace.push_back(row);
}
extern "C" void real_add(P *, Core::Portable::IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE");
extern "C" void real_remove(P *, Core::Portable::IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrap_add(P *p, Core::Portable::IParamObserver *o) asm(
    "__wrap__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE");
extern "C" void wrap_remove(P *p, Core::Portable::IParamObserver *o) asm(
    "__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrap_add(P *p, Core::Portable::IParamObserver *o) {
  observe(1, p, o);
  real_add(p, o);
}
extern "C" void wrap_remove(P *p, Core::Portable::IParamObserver *o) {
  observe(0, p, o);
  real_remove(p, o);
}
static BP read() {
  std::array<int, 6> ids{};
  for (auto &id : ids)
    std::cin >> id;
  auto p = [&](int i) -> P * { return ids[i] ? pool.at(ids[i] - 1) : nullptr; };
  return {p(1), p(2), p(3), p(0), p(4), p(5)};
}
int main() {
  int mode, nonnull, index, count;
  while (std::cin >> mode >> nonnull >> index >> count) {
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.minValue = 0;
    info.maxValue = 100;
    std::vector<std::unique_ptr<Parameter>> params;
    pool.clear();
    for (int i = 0; i < 12; ++i) {
      params.emplace_back(std::make_unique<Parameter>(info));
      pool.push_back(params.back().get());
    }
    EQ eq(presonus::dsp::EQControlBiquadPortTag{});
    Core::Portable::Control control;
    eq.bindPortableControl(control);
    owner = &eq;
    selected = index;
    auto old = read(), next = read();
    eq.portableBandState().resize(count);
    eq.portableParameterState().assign(count, old);
    std::vector<P *> types(count, old.slot3);
    eq.bindPortableTypeParameters(types);
    for (auto &b : eq.portableBandState())
      b.dirty = 7;
    recording = false;
    if (mode == 0)
      old.addObserver(nonnull ? &eq : nullptr);
    if (mode == 2)
      for (auto &b : eq.portableParameterState())
        b.addObserver(&eq);
    trace.clear();
    recording = true;
    if (mode == 0)
      old.removeObserver(nonnull ? &eq : nullptr);
    else if (mode == 1)
      old.addObserver(nonnull ? &eq : nullptr);
    else
      eq.setBand(index, next);
    recording = false;
    std::cout << trace.size();
    for (auto row : trace)
      for (int v : row)
        std::cout << ' ' << v;
    for (const auto &b : eq.portableParameterState())
      for (int v : raw(b))
        std::cout << ' ' << v;
    for (const auto &b : eq.portableBandState())
      std::cout << ' ' << static_cast<int>(b.dirty);
    for (auto &p : params)
      std::cout << ' ' << p->members();
    // Actual provider notification -> existing EQ observer -> dirty effects.
    // Null observer is forwarded but never notified (provider precondition).
    if (nonnull) {
      for (auto &p : params) {
        for (auto &b : eq.portableBandState())
          b.dirty = 0;
        p->changed();
        for (const auto &b : eq.portableBandState())
          std::cout << ' ' << static_cast<int>(b.dirty);
      }
    }
    std::cout << '\n';
    // Avoid provider destruction callbacks after borrowed owner lifetime ends.
    for (auto &p : params)
      while (p->members())
        p->removeObserver(nonnull ? eq.portableObserver() : nullptr);
  }
}
