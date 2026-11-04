#include "presonus/reconstruction200/large02_w03.hpp"
#include <bit>
#include <cstdlib>
#include <iostream>
#include <vector>
using U = std::uint32_t;
using namespace Presonus::Dsp;
// Test-only direct invocation of compiler-emitted ABI destructor entry.
extern "C" void controllerDeletingDestructor(Controller *) asm(
    "_ZN8Presonus3Dsp10ControllerD0Ev");
static void *watched = nullptr;
static U frees = 0;
void operator delete(void *p) noexcept {
  if (p == watched)
    ++frees;
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
struct Handler : Core::IPropertyHandler {
  U releases = 0, sends = 0;
  std::vector<U> payload;
  void setProperty(const Core::Property &p) override {
    ++sends;
    if (p.type == 0x6d627164) {
      const auto &c = static_cast<const ChannelProperty &>(p);
      payload = {U(c.channel), U(c.count)};
      for (int i = 0; i < c.count; ++i) {
        payload.push_back(U(c.entries[i].band));
        for (float v : c.entries[i].coefficients)
          payload.push_back(std::bit_cast<U>(v));
      }
    }
  }
  void getProperty(Core::Property &) override {}
  void release() override { ++releases; }
};
struct Test : Controller {
  std::vector<U> calls;
  U updates = 0;
  bool forwardSetup = false;
  Test() : Controller(presonus::dsp::ControllerSourceTag{}) {}
  float getValue(int) const override { return 0.f; }
  float setValue(int i, float f) override {
    calls.insert(calls.end(), {20, U(i), std::bit_cast<U>(f)});
    return f;
  }
  void setupProcess(const SetupProperty &p) override {
    calls.push_back(80);
    if (forwardSetup)
      Controller::setupProcess(p);
  }
  void doUpdates() override { ++updates; }
};
static void bands(std::vector<U> &o, const EQController &e) {
  o.push_back(U(const_cast<EQController &>(e).portableEnabled()));
  o.push_back(e.sourceState().processDirty);
  for (auto &b : e.portableBands())
    o.insert(o.end(),
             {U(b.type), std::bit_cast<U>(b.frequency), std::bit_cast<U>(b.q),
              std::bit_cast<U>(b.gain), b.edgeSelectable, b.dirty, b.enabled,
              b.calculator.portableState().byte48});
}
int main() {
  int m, n;
  while (std::cin >> m >> n) {
    std::vector<U> a(n), o;
    for (auto &v : a)
      std::cin >> v;
    auto i = [&](unsigned k) { return std::bit_cast<int>(a.at(k)); };
    Handler h, h2;
    Test x;
    auto &s = x.sourceState();
    if (m == 1) {
      struct P : Core::Property {
        U w8, w12, w16;
        P() : Property(0, sizeof(P)) {}
      } p;
      p.type = i(0);
      p.w8 = a[1];
      p.w12 = a[2];
      p.w16 = a[4];
      if (p.type == 1348563553)
        p.w12 = a[3];
      s.word04 = 111;
      if (p.type == 1399157877) {
        SetupProperty setup;
        x.forwardSetup = a.size() > 5 && a[5];
        setup.rate = std::bit_cast<float>(a[1]);
        x.setProperty(setup);
      } else
        x.setProperty(p);
      o = {s.word04, s.processDirty, s.byte1d};
      o.insert(o.end(), x.calls.begin(), x.calls.end());
      if (a.size() > 5 && a[5])
        o.push_back(s.processRateBits);
    } else if (m == 2) {
      ChannelProperty p;
      p.channel = i(3);
      s.word04 = a[2];
      s.target = a[0] ? &h : nullptr;
      x.sendProperty(p, a[1]);
      o = {U(p.channel), h.sends};
    } else if (m == 3 || m == 11) {
      ParamDescriptorList list(presonus::dsp::DescriptorSourceTag{});
      for (int k = 0; k < i(0); ++k)
        list.addToggle(10 + k, "", "", "", float(k) * .25f, "", 0);
      if (a[0] != 0xffffffffu) {
        s.descriptorList = &list;
        s.descriptors = &list.sourceDescriptors();
      }
      if (m == 3) {
        x.setDefaultValues();
        o = x.calls;
      } else
        o = {U(x.getNumParameters())};
      s.descriptorList = nullptr;
      s.descriptors = nullptr;
    } else if (m == 4) {
      s.constructorId = i(0);
      o = {U(x.canFloatPrecision(i(1)))};
    } else if (m == 5) {
      x.setHandler(a[0] ? &h : nullptr);
      o = {U(s.handler != nullptr)};
    } else if (m == 6) {
      s.constructorId = i(0);
      o = {U(x.canConfiguration(i(1), i(2)))};
    } else if (m == 7) {
      x.makeTargetOwner();
      o = {s.byte1d};
    } else if (m == 8) {
      s.constructorId = i(0);
      SetupProperty p;
      p.inputs = i(1);
      p.outputs = i(2);
      p.precision = i(3);
      o = {U(x.canSetup(p))};
    } else if (m == 9 || m == 15) {
      EQController e(2, 7, nullptr);
      auto &b = e.portableBands();
      e.portableEnabled() = a[m == 9 ? 2 : 1];
      e.sourceState().processDirty = m == 9 ? a[3] : 0;
      for (auto &v : b) {
        v.enabled = a[m == 9 ? 4 : 2];
        v.edgeSelectable = a[m == 9 ? 5 : 3];
      }
      if (m == 9) {
        e.setValue(i(0), std::bit_cast<float>(a[1]));
        bands(o, e);
      } else {
        for (auto &v : b) {
          v.type = i(4);
          v.frequency = std::bit_cast<float>(a[5]);
          v.q = std::bit_cast<float>(a[6]);
          v.gain = std::bit_cast<float>(a[7]);
        }
        o = {std::bit_cast<U>(e.getValue(i(0)))};
      }
    } else if (m == 10) {
      s.constructorId = i(0);
      o = {U(x.usedInProcessContext())};
    } else if (m == 12 || m == 20) {
      auto *p = new Test;
      p->sourceState().target = a[1] ? &h : nullptr;
      p->sourceState().byte1d = a[0];
      watched = p;
      frees = 0;
      if (m == 12)
        p->release();
      else
        controllerDeletingDestructor(p);
      o = {h.releases, frees};
      watched = nullptr;
    } else if (m == 13) {
      Core::Property p(i(1), 8);
      s.target = a[0] ? &h : nullptr;
      x.sendProperty(p);
      o = {h.sends};
    } else if (m == 14) {
      s.target = a[0] ? &h : nullptr;
      s.byte1d = a[2];
      x.setTarget(a[1] == 1 ? &h : a[1] == 2 ? &h2 : nullptr);
      o = {h.releases, U(s.target == &h ? 1 : s.target == &h2 ? 2 : 0)};
      s.byte1d = 0;
    } else if (m == 16) {
      s.processDirty = a[0];
      s.target = a[1] ? &h : nullptr;
      s.processRateBits = a[2];
      s.word20 = a[3];
      auto r = x.flushParameterChanges();
      o = {r, s.processDirty, s.word20, x.updates};
    } else if (m == 17 || m == 19) {
      {
        Test p;
        p.sourceState().target = a[1] ? &h : nullptr;
        p.sourceState().byte1d = a[0];
      }
      o = {h.releases, 0};
    } else if (m == 18) {
      EQController e(i(0), 7, nullptr);
      e.portableEnabled() = a[1];
      e.sourceState().word04 = 55;
      e.setTarget(a[3] ? &h : nullptr);
      SetupProperty setup;
      setup.rate = 48000.f;
      e.setupProcess(setup);
      if (!a[4])
        e.sourceState().processDirty = 0;
      for (unsigned k = 0; k < e.portableBands().size(); ++k) {
        auto &b = e.portableBands()[k];
        b.calculator.setup(32, 48000);
        b.dirty = (a[2] >> k) & 1;
        b.enabled = 1;
      }
      U flushed = 0;
      if (a[4])
        flushed = e.flushParameterChanges();
      else
        e.doUpdates();
      o = {e.sourceState().processDirty, h.sends};
      for (auto &b : e.portableBands())
        o.push_back(b.dirty);
      o.insert(o.end(), h.payload.begin(), h.payload.end());
      if (a[4])
        o.push_back(flushed);
    } else if (m == 21 || m == 23) {
      EQController e(i(0), i(1), nullptr);
      bands(o, e);
      o.insert(o.begin(), U(e.getNumBands()));
    } else if (m == 22) {
      auto *p = new EQController(2, 7, nullptr);
      p->sourceState().target = a[1] ? &h : nullptr;
      p->sourceState().byte1d = a[0];
      watched = p;
      frees = 0;
      delete p;
      o = {h.releases, frees};
      watched = nullptr;
    } else if (m == 24 || m == 25) {
      {
        EQController e(2, 7, nullptr);
        e.sourceState().target = a[1] ? &h : nullptr;
        e.sourceState().byte1d = a[0];
      }
      o = {h.releases, 0};
    } else
      return 2;
    std::cout << o.size();
    for (U v : o)
      std::cout << ' ' << v;
    std::cout << '\n';
  }
}
