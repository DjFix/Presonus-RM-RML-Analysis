#include "presonus/surface/FXEditPageComponent.hpp"
#include "presonus/surface/FXHomePageComponent.hpp"
#include "presonus/surface/FxPresetsPageComponent.hpp"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string>
#include <vector>
using Core::Portable::AliasParam;
using Core::Portable::IParamObserver;
using Core::Portable::Parameter;
namespace presonus::surface {
struct FXPageTestAccess {
  static void observe(Presonus::Surface::FXEditPageComponent &p, Parameter *v) {
    v->addObserver(&p);
    assert(p.observed_.add(v));
  }
  static void mappable(Presonus::Surface::FXEditPageComponent &p,
                       Parameter *v) {
    assert(p.mappables_.add(v));
  }
  template <class T> static void alias(T &p, AliasParam *v) {
    assert(p.aliases_.add(v));
  }
  static auto observed(Presonus::Surface::FXEditPageComponent &p) {
    return p.observed_.getItems();
  }
  static auto mappables(Presonus::Surface::FXEditPageComponent &p) {
    return p.mappables_.getItems();
  }
  template <class T> static auto aliases(T &p) { return p.aliases_.getItems(); }
};
} // namespace presonus::surface
namespace {
bool active = false;
void *watched = nullptr, *storage[3]{};
void *ownedChild = nullptr, *ownedParameter = nullptr;
bool childFreed = false, parameterFreed = false, objectFreed = false;
int storageFreed = 0, baseCalls = 0;
IParamObserver *pageObserver = nullptr;
Parameter *parameters[3]{};
AliasParam *aliasObjects[3]{};
std::vector<int> removed, disconnected;
void onFree(void *p) {
  if (!active || !p)
    return;
  if (p == watched) {
    assert(!objectFreed);
    objectFreed = true;
  }
  if (p == ownedChild)
    childFreed = true;
  if (p == ownedParameter)
    parameterFreed = true;
  for (auto &s : storage)
    if (s && p == s) {
      ++storageFreed;
      s = nullptr;
    }
}
struct InspectableParam : Core::Portable::NumericParam {
  using NumericParam::NumericParam;
  int observers() const { return observerList.count(); }
};
void print(const std::vector<int> &v) {
  for (int x : v)
    std::cout << x << ' ';
  std::cout << '\n';
}
void hex(const char *p) {
  static const char h[] = "0123456789abcdef";
  if (!*p)
    std::cout << '-';
  for (; *p; ++p) {
    auto c = static_cast<unsigned char>(*p);
    std::cout << h[c >> 4] << h[c & 15];
  }
}
} // namespace
extern "C" {
void __real__ZdlPv(void *);
void __real__ZdlPvm(void *, std::size_t);
void __real__ZdaPv(void *);
void __real__ZdaPvm(void *, std::size_t);
void __wrap__ZdlPv(void *p) {
  onFree(p);
  __real__ZdlPv(p);
}
void __wrap__ZdlPvm(void *p, std::size_t n) {
  onFree(p);
  __real__ZdlPvm(p, n);
}
void __wrap__ZdaPv(void *p) {
  onFree(p);
  __real__ZdaPv(p);
}
void __wrap__ZdaPvm(void *p, std::size_t n) {
  onFree(p);
  __real__ZdaPvm(p, n);
}
void __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
void __wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *o) {
  if (active && o == pageObserver) {
    int i = 0;
    while (i < 3 && parameters[i] != p)
      ++i;
    assert(i < 3);
    removed.push_back(i);
  }
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(p,
                                                                            o);
}
void __real__ZN4Core8Portable10AliasParam11setOriginalEPNS0_9ParameterE(
    AliasParam *, Parameter *);
void __wrap__ZN4Core8Portable10AliasParam11setOriginalEPNS0_9ParameterE(
    AliasParam *p, Parameter *o) {
  if (active) {
    for (int i = 0; i < 3; ++i)
      if (aliasObjects[i] == p) {
        assert(!o);
        disconnected.push_back(i);
      }
  }
  __real__ZN4Core8Portable10AliasParam11setOriginalEPNS0_9ParameterE(p, o);
}
void __real__ZN4Core8Portable9ComponentD2Ev(Core::Portable::Component *);
void __wrap__ZN4Core8Portable9ComponentD2Ev(Core::Portable::Component *p) {
  if (active && p == watched)
    ++baseCalls;
  __real__ZN4Core8Portable9ComponentD2Ev(p);
}
void editD1(Presonus::Surface::FXEditPageComponent *) asm(
    "_ZN8Presonus7Surface19FXEditPageComponentD1Ev");
void editD2(Presonus::Surface::FXEditPageComponent *) asm(
    "_ZN8Presonus7Surface19FXEditPageComponentD2Ev");
void editD0(Presonus::Surface::FXEditPageComponent *) asm(
    "_ZN8Presonus7Surface19FXEditPageComponentD0Ev");
void presetD1(Presonus::Surface::FxPresetsPageComponent *) asm(
    "_ZN8Presonus7Surface22FxPresetsPageComponentD1Ev");
void presetD0(Presonus::Surface::FxPresetsPageComponent *) asm(
    "_ZN8Presonus7Surface22FxPresetsPageComponentD0Ev");
void homeD1(Presonus::Surface::FXHomePageComponent *) asm(
    "_ZN8Presonus7Surface19FXHomePageComponentD1Ev");
void homeD0(Presonus::Surface::FXHomePageComponent *) asm(
    "_ZN8Presonus7Surface19FXHomePageComponentD0Ev");
}
int main() {
  using namespace Presonus::Surface;
  using Access = presonus::surface::FXPageTestAccess;
  char mode;
  while (std::cin >> mode) {
    if (mode == 'U' || mode == 'P') {
      std::int32_t v;
      int length;
      std::cin >> v >> length;
      std::string prefix(length, 'p');
      Core::CString256 out(prefix.c_str());
      if (mode == 'U') {
        FxPresetsPageComponent p(v);
        auto &ret = p.getTargetUrl(out);
        hex(out.str());
        std::cout << ' ' << (&ret == &out) << '\n';
      } else {
        auto &ret = out.appendFormat("fx/ch%d", v);
        hex(out.str());
        std::cout << ' ' << (&ret == &out) << '\n';
      }
      continue;
    }
    int task, n, m, a;
    std::cin >> task >> n >> m >> a;
    Core::Portable::ParamInfo info[3];
    const char *names[] = {"p0", "p1", "p2"};
    for (int i = 0; i < 3; ++i) {
      info[i].clear();
      info[i].type = Core::Portable::ParamInfo::kFloat;
      info[i].tag = i;
      std::strncpy(info[i].name, names[i], 31);
      info[i].maxValue = 100;
    }
    InspectableParam p0(info[0]), p1(info[1]), p2(info[2]);
    parameters[0] = &p0;
    parameters[1] = &p1;
    parameters[2] = &p2;
    AliasParam a0(info[0]), a1(info[1]), a2(info[2]);
    aliasObjects[0] = &a0;
    aliasObjects[1] = &a1;
    aliasObjects[2] = &a2;
    a0.setOriginal(&p0);
    a2.setOriginal(&p1);
    removed.clear();
    disconnected.clear();
    objectFreed = false;
    storageFreed = baseCalls = 0;
    childFreed = parameterFreed = false;
    for (auto &s : storage)
      s = nullptr;
    if (task == 4) {
      FXEditPageComponent p;
      Parameter *entries[] = {nullptr, &p0, &a0, &a1, &a2};
      for (int i = 0; i < n; ++i) {
        int type;
        std::cin >> type;
        Access::mappable(p, entries[type]);
      }
      active = true;
      p.disconnectMappables();
      active = false;
      std::vector<int> result{static_cast<int>(disconnected.size())};
      result.insert(result.end(), disconnected.begin(), disconnected.end());
      for (auto *q : aliasObjects)
        result.push_back(q->getOriginal() != nullptr);
      print(result);
    } else {
      void *mem = nullptr;
      FXEditPageComponent *edit = nullptr;
      FxPresetsPageComponent *preset = nullptr;
      FXHomePageComponent *home = nullptr;
      Core::Portable::Component *component = nullptr;
      if (task <= 5) {
        mem = ::operator new(sizeof(FXEditPageComponent));
        edit = new (mem) FXEditPageComponent;
        component = edit;
        pageObserver = edit;
        for (int i = 0; i < n; ++i)
          Access::observe(*edit, parameters[i % 3]);
        for (int i = 0; i < m; ++i)
          Access::mappable(*edit, parameters[i % 3]);
        for (int i = 0; i < a; ++i)
          Access::alias(*edit, aliasObjects[i % 3]);
        storage[0] = Access::observed(*edit);
        storage[1] = Access::mappables(*edit);
        storage[2] = Access::aliases(*edit);
      } else if (task < 18) {
        mem = ::operator new(sizeof(FxPresetsPageComponent));
        preset = new (mem) FxPresetsPageComponent;
        component = preset;
        for (int i = 0; i < a; ++i)
          Access::alias(*preset, aliasObjects[i % 3]);
        storage[0] = Access::aliases(*preset);
      } else {
        mem = ::operator new(sizeof(FXHomePageComponent));
        home = new (mem) FXHomePageComponent;
        component = home;
        for (int i = 0; i < a; ++i)
          Access::alias(*home, aliasObjects[i % 3]);
        storage[0] = Access::aliases(*home);
      }
      // Actual CCL provider owns these objects and must free them. Their native
      // internal implementation is excluded from application-range execution.
      auto *child = new Core::Portable::Component("owned-child");
      component->addChild(child);
      ownedChild = child;
      component->addParameters(&info[2], 1, false);
      ownedParameter = component->getParameterByTag(2);
      assert(ownedParameter);
      watched = mem;
      active = true;
      if (task == 2)
        editD2(edit);
      else if (task == 3)
        editD1(edit);
      else if (task == 5)
        editD0(edit);
      else if (task == 13)
        presetD1(preset);
      else if (task == 14)
        presetD0(preset);
      else if (task == 18)
        homeD1(home);
      else if (task == 19)
        homeD0(home);
      else
        std::abort();
      active = false;
      assert(childFreed && parameterFreed);
      assert(p0.observers() == 1 && p1.observers() == 1 && p2.observers() == 0);
      std::vector<int> result{static_cast<int>(removed.size())};
      result.insert(result.end(), removed.begin(), removed.end());
      result.push_back(baseCalls);
      result.push_back(objectFreed);
      result.push_back(storageFreed);
      print(result);
      if (!objectFreed)
        ::operator delete(mem);
    }
    active = false;
    a0.setOriginal(nullptr);
    a1.setOriginal(nullptr);
    a2.setOriginal(nullptr);
  }
}
