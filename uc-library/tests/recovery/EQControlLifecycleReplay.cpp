#include "presonus/mixer_dsp/EQControl.hpp"
#include <array>
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
using EQ = Presonus::EQControl;
using P = Core::Portable::Parameter;
namespace {
struct Image : Core::Portable::Bitmap {
  int refs() const { return useCount; }
};
struct Parameter : Core::Portable::NumericParam {
  using NumericParam::NumericParam;
  int members() const { return observerList.count(); }
};
struct Event {
  int kind, id, a, b, c;
};
std::array<Event, 512> events;
int nevents = 0;
bool recording = false;
std::array<void *, 32> allocations{};
std::array<P *, 9> parameters{};
std::array<Image *, 3> images{};
Core::Portable::IParamObserver *eqObserver = nullptr;
int objectFrees = 0, bitmapDeaths = 0, parameterDeaths = 0;
void event(int kind, int id) {
  if (recording) {
    assert(nevents < static_cast<int>(events.size()));
    events[nevents++] = {kind, id, images[0]->refs(), images[1]->refs(),
                         images[2]->refs()};
  }
}
void allocation(void *p) {
  if (!recording)
    return;
  for (unsigned i = 0; i < allocations.size(); ++i)
    if (p && allocations[i] == p) {
      event(2, i);
      if (i == 0)
        ++objectFrees;
      allocations[i] = nullptr;
    }
}
struct OwnedBitmap : Core::Portable::Bitmap {
  ~OwnedBitmap() override {
    ++bitmapDeaths;
    event(3, 0);
  }
};
struct Lifetime : Core::Portable::ParamObserverBase {
  void paramChanged(P *p, int msg) override {
    assert(msg == P::kDestroyed);
    ++parameterDeaths;
    for (unsigned i = 6; i < 9; ++i)
      if (parameters[i] == p)
        event(4, i);
    p->removeObserver(this);
  }
};
} // namespace
extern "C" void realDelete(void *) asm("__real__ZdlPv");
extern "C" void realSizedDelete(void *, std::size_t) asm("__real__ZdlPvm");
extern "C" void wrapDelete(void *) asm("__wrap__ZdlPv");
extern "C" void wrapSizedDelete(void *, std::size_t) asm("__wrap__ZdlPvm");
extern "C" void wrapDelete(void *p) {
  allocation(p);
  realDelete(p);
}
extern "C" void wrapSizedDelete(void *p, std::size_t n) {
  allocation(p);
  realSizedDelete(p, n);
}
extern "C" void realRemove(P *, Core::Portable::IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrapRemove(P *, Core::Portable::IParamObserver *) asm(
    "__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrapRemove(P *p, Core::Portable::IParamObserver *o) {
  if (recording && o == eqObserver) {
    bool found = false;
    for (unsigned i = 0; i < parameters.size(); ++i)
      if (parameters[i] == p) {
        event(1, i + 1);
        found = true;
        break;
      }
    assert(found);
  }
  realRemove(p, o);
}
extern "C" void d1(EQ *) asm("_ZN8Presonus9EQControlD1Ev");
extern "C" void d2(EQ *) asm("_ZN8Presonus9EQControlD2Ev");
int main() {
  int variant, count, pattern, mask, constructed;
  while (std::cin >> variant >> count >> pattern >> mask >> constructed) {
    Image first, second, third;
    images = {&first, &second, &third};
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.maxValue = 100;
    std::array<std::unique_ptr<Parameter>, 6> pool;
    for (unsigned i = 0; i < 6; ++i) {
      pool[i] = std::make_unique<Parameter>(info);
      parameters[i] = pool[i].get();
    }
    parameters[6] = parameters[7] = parameters[8] = nullptr;
    Parameter primary(info);
    Core::Portable::Control borrowed;
    borrowed.setParameter(&primary);
    void *storage = ::operator new(sizeof(EQ));
    EQ *eq = constructed ? new (storage) EQ(Core::Rect(0, 0, 32, 16))
                         : new (storage)
                               EQ(presonus::dsp::EQControlBiquadPortTag{});
    eqObserver = eq->portableObserver();
    eq->bindPortableControl(borrowed);
    Lifetime lifetime;
    if (constructed) {
      auto *state = const_cast<EQ::PortableConstructorState *>(
          eq->portableConstructorState());
      state->control.setParameter(&primary);
      eq->bindPortableControl(state->control);
      for (int i = 0; i < 3; ++i) {
        parameters[i + 6] = state->hpfParameters.at(i);
        parameters[i + 6]->addObserver(&lifetime);
      }
    }
    eq->portableBandState().resize(count);
    eq->portableParameterState().resize(count);
    std::vector<P *> types(count);
    for (int i = 0; i < count; ++i) {
      std::array<P *, 6> raw{};
      for (int s = 0; s < 6; ++s) {
        int id = pattern == 0   ? 0
                 : pattern == 1 ? s + 1
                 : pattern == 2 ? 1
                                : ((s + i) % 2 ? s + 1 : 0);
        raw[s] = id ? parameters[id - 1] : nullptr;
      }
      if (constructed && i == 0) {
        raw[0] = parameters[8];
        raw[1] = parameters[7];
        raw[2] = parameters[6];
      }
      EQ::BandParams b{raw[1], raw[2], raw[3], raw[0], raw[4], raw[5]};
      eq->portableParameterState()[i] = b;
      types[i] = raw[0];
      b.addObserver(eq);
      // Deliberately stale compatibility slot3: lifecycle must use type vector.
      eq->portableParameterState()[i].slot3 = parameters[5];
    }
    eq->bindPortableTypeParameters(types);
    allocations.fill(nullptr);
    allocations[0] = storage;
    if (mask & 1) {
      eq->portableAmplitudeCurve().assign(11, 1);
      allocations[1] = eq->portableAmplitudeCurve().data();
      eq->portablePixelCurve().assign(11, 1);
      allocations[2] = eq->portablePixelCurve().data();
    }
    if (mask & 2) {
      auto &curves = eq->portableBandCurveStorage();
      curves.resize(count);
      std::vector<Core::Portable::Bitmap *> refs;
      for (int i = 0; i < count; ++i) {
        curves[i].assign(11, 1);
        allocations[3 + i] = curves[i].data();
        refs.push_back(images[i % 3]);
      }
      eq->bindPortableBandImages(refs);
      eq->bindPortableImages(&first, &second);
    }
    if (mask & 4) {
      auto p = std::make_unique<OwnedBitmap>();
      allocations[10] = p.get();
      eq->bindPortableOwnedBitmap(std::move(p));
    }
    // Actual CCL changed() proves membership/callbacks before teardown.
    if (count) {
      parameters[0]->changed();
    }
    nevents = objectFrees = bitmapDeaths = parameterDeaths = 0;
    recording = true;
    if (variant == 0)
      delete eq;
    else if (variant == 1)
      d1(eq);
    else
      d2(eq);
    recording = false;
    assert(objectFrees == (variant == 0));
    if (variant != 0)
      ::operator delete(storage);
    assert(first.refs() == 0 && second.refs() == 0 && third.refs() == 0);
    for (const auto &p : pool)
      assert(p->members() == 0);
    assert(primary.members() ==
           1); // borrowed Control still owns its registration
    borrowed.setParameter(nullptr);
    assert(primary.members() == 0);
    assert(parameterDeaths == (constructed ? 3 : 0));
    assert(bitmapDeaths == ((mask & 4) ? 1 : 0));
    std::cout << nevents;
    for (int i = 0; i < nevents; ++i) {
      auto e = events[i];
      std::cout << ' ' << e.kind << ' ' << e.id << ' ' << e.a << ' ' << e.b
                << ' ' << e.c;
    }
    std::cout << ' ' << objectFrees << ' ' << bitmapDeaths << ' '
              << parameterDeaths << '\n';
  }
}
