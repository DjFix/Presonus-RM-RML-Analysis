#include "presonus/surface/DawFxPageComponent.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string_view>

namespace Presonus::Surface {
struct DawFxTestAccess {
  static bool modeBound(DawFxPageComponent &page) {
    return page.mode_ && page.mode_ == page.getParameterByTag(1000);
  }
  static void state(const DawFxPageComponent &page) {
    std::cout << (page.dawClient_ != nullptr) << ' '
              << (page.mappingController_ != nullptr) << ' '
              << page.insertOffset_ << ' ' << page.sendOffset_ << '\n';
  }
};
} // namespace Presonus::Surface

namespace {
using Core::Portable::AliasParam;
using Core::Portable::Component;
using Core::Portable::NumericParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Core::Portable::StringParam;
using Presonus::Surface::DawFxPageComponent;
using Presonus::Surface::DawFxTestAccess;

enum Allocation { Receiver, Child, Parameter };
std::array<std::uintptr_t, 3> allocations{};
std::array<int, 3> frees{};
std::array<int, 3> order{};
int sequence = 0;
int childDestructions = 0;
const char *receiverDelete = nullptr;

void recordReturnedDelete(std::uintptr_t memory, const char *overload) {
  for (std::size_t i = 0; i < allocations.size(); ++i) {
    if (allocations[i] && allocations[i] == memory) {
      ++frees[i];
      order[i] = ++sequence;
      if (i == Receiver)
        receiverDelete = overload;
    }
  }
}

class OwnedChild : public Component {
public:
  ~OwnedChild() override { ++childDestructions; }
};

[[gnu::noinline, gnu::noclone]] void dispose(Component *object) {
  delete object;
}

struct ParamInfoMember {
  using Member = const ParamInfo *Parameter::*;
  friend Member get(ParamInfoMember);
};
template <class Tag, typename Tag::Member pointer> struct ParameterAccess {
  friend typename Tag::Member get(Tag) { return pointer; }
};
template struct ParameterAccess<ParamInfoMember, &Parameter::info>;

extern "C" void
completeConstruct(DawFxPageComponent *, const char *,
                  int) asm("_ZN8Presonus7Surface18DawFxPageComponentC1EPKci");
extern "C" void
baseConstruct(DawFxPageComponent *, const char *,
              int) asm("_ZN8Presonus7Surface18DawFxPageComponentC2EPKci");
extern "C" void completeDestroy(DawFxPageComponent *) asm(
    "_ZN8Presonus7Surface18DawFxPageComponentD1Ev");

void emitConstructor(DawFxPageComponent &page) {
  std::cout << page.getName() << ' ' << page.getFormName() << ' '
            << page.getPageTag() << ' ' << DawFxTestAccess::modeBound(page)
            << '\n';
  DawFxTestAccess::state(page);
  std::cout << page.countParameters() << '\n';
  for (int i = 0; i < page.countParameters(); ++i) {
    auto *param = page.getParameterAt(i);
    const auto &info = *(param->*get(ParamInfoMember{}));
    auto *alias = AliasParam::cast(param);
    if ((info.type == ParamInfo::kAlias && (!alias || alias->getOriginal())) ||
        (info.type == ParamInfo::kString && !StringParam::cast(param)) ||
        ((info.type == ParamInfo::kToggle || info.type == ParamInfo::kInt) &&
         !Core::Portable::core_cast<NumericParam>(param)))
      std::abort();
    std::cout << info.type << ' ' << info.tag << ' ' << info.name << ' '
              << info.minValue << ' ' << info.maxValue << ' ' << info.midValue
              << ' ' << info.defaultValue << ' ' << info.deltaValue << ' '
              << info.flags << ' '
              << bool(info.unitName || info.curveName || info.stringList ||
                      info.title || info.shortTitle)
              << ' ' << param->isOwnInfo() << '\n';
  }
}

void run(bool deleting, bool base) {
  allocations = {};
  frees = {};
  order = {};
  sequence = 0;
  childDestructions = 0;
  receiverDelete = nullptr;

  auto *page = static_cast<DawFxPageComponent *>(
      ::operator new(sizeof(DawFxPageComponent)));
  auto construct = base ? baseConstruct : completeConstruct;
  construct(page, deleting ? "another-form" : "recovery-fx",
            deleting ? 23 : 77);
  page = std::launder(page);
  emitConstructor(*page);
  auto *child = new OwnedChild;
  allocations[Receiver] = reinterpret_cast<std::uintptr_t>(page);
  allocations[Child] = reinterpret_cast<std::uintptr_t>(child);
  allocations[Parameter] =
      reinterpret_cast<std::uintptr_t>(page->getParameterByTag(0));
  page->addChild(child);

  if (deleting)
    dispose(page);
  else
    completeDestroy(page);
  if (frees[Receiver] != static_cast<int>(deleting) || frees[Child] != 1 ||
      frees[Parameter] != 1 || childDestructions != 1 ||
      (deleting &&
       !(order[Child] < order[Receiver] && order[Parameter] < order[Receiver])))
    std::abort();
  std::cout << frees[Receiver] << ' ' << frees[Child] << ' ' << frees[Parameter]
            << ' ' << (receiverDelete ? receiverDelete : "none") << '\n';
  if (!deleting) {
    allocations = {};
    ::operator delete(page);
  }
}
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);

extern "C" void __wrap__ZdlPv(void *memory) {
  const auto address = reinterpret_cast<std::uintptr_t>(memory);
  __real__ZdlPv(memory);
  recordReturnedDelete(address, "unsized");
}

extern "C" void __wrap__ZdlPvm(void *memory, std::size_t size) {
  const auto address = reinterpret_cast<std::uintptr_t>(memory);
  __real__ZdlPvm(memory, size);
  recordReturnedDelete(address, "sized");
}

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const bool base = std::string_view(argv[1]) == "base";
  run(false, base);
  run(true, base);
}
