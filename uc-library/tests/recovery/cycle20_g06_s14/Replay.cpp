#include "presonus/panel/FieldElement.hpp"
#include "presonus/panel/LCDManager.hpp"
#include "presonus/panel/TextEntryElement.hpp"

#include <algorithm>
#include <cerrno>
#include <cstddef>
#include <cstring>
#include <iostream>
#include <new>
#include <string_view>
#include <sys/mman.h>

using Core::Portable::IParamObserver;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Core::Portable::StringParam;
using namespace Presonus::Panel;

namespace {
std::string calls;
IParamObserver *observedReceiver = nullptr;
void *mappedReceiver = nullptr;
bool mapNextAllocation = false;
int disposalResult = -1;

class Delegate : public ILCDDelegate {
public:
  Parameter *result = nullptr;
  Parameter *lookupElementParameter(const char *name) const override {
    if (std::strcmp(name, "panel/level"))
      std::abort();
    calls.push_back('d');
    return result;
  }
};

std::string toHex(std::string_view bytes) {
  std::string result;
  constexpr std::string_view digits = "0123456789abcdef";
  for (unsigned char byte : bytes) {
    result += digits[byte >> 4];
    result += digits[byte & 15];
  }
  return result.empty() ? "-" : result;
}

std::string fromHex(std::string_view value) {
  constexpr std::string_view digits = "0123456789abcdef";
  std::string result;
  if (value == "-" || value == "~")
    return result;
  for (std::size_t i = 0; i < value.size(); i += 2)
    result += static_cast<char>((digits.find(value[i]) << 4) |
                                digits.find(value[i + 1]));
  return result;
}

[[gnu::noinline]] void destroy(Element *receiver) { delete receiver; }
} // namespace

extern "C" void realAdd(Parameter *, IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE");
extern "C" void wrapAdd(Parameter *, IParamObserver *) asm(
    "__wrap__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE");
extern "C" void realRemove(Parameter *, IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrapRemove(Parameter *, IParamObserver *) asm(
    "__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void
fieldBaseDestructor(FieldElement *) asm("_ZN8Presonus5Panel12FieldElementD2Ev");

extern "C" void wrapAdd(Parameter *parameter, IParamObserver *observer) {
  realAdd(parameter, observer);
  observedReceiver = observer;
  calls.push_back('a');
}

extern "C" void wrapRemove(Parameter *parameter, IParamObserver *observer) {
  if (observer != observedReceiver)
    std::abort();
  realRemove(parameter, observer);
  calls.push_back('r');
}

extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__wrap__Znwm(std::size_t size) {
  if (!mapNextAllocation)
    return __real__Znwm(size);
  mapNextAllocation = false;
  mappedReceiver = mmap(nullptr, 4096, PROT_READ | PROT_WRITE,
                        MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (mappedReceiver == MAP_FAILED)
    throw std::bad_alloc{};
  return mappedReceiver;
}

extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *receiver) {
  if (mappedReceiver && receiver == mappedReceiver) {
    if (!calls.empty() && calls != "r")
      std::abort();
    disposalResult = munmap(receiver, 4096);
    return;
  }
  __real__ZdlPv(receiver);
}

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::string_view test(argv[1]);
  ParamInfo info{};
  StringParam first(info), second(info);
  bool bound;
  int initial, refresh, managerBound, target, variant;
  std::string token;
  Delegate delegate;
  LCDManager manager(LCDManager::SourcePortConstruction{});
  manager.setDelegate(&delegate);
  Parameter *parameters[] = {nullptr, &first, &second};

  if (test == "field-lookup" || test == "field-get") {
    while (std::cin >> initial >> refresh >> managerBound >> target) {
      FieldElement field("panel/level", &manager);
      delegate.result = parameters[initial];
      if (initial)
        field.lookupParameters();
      field.setRefreshParameter(refresh != 0);
      field.setDirty(7);
      delegate.result = parameters[target];
      calls.clear();
      // Switch the portable manager's delegate off for the unbound path.
      // A separately constructed unbound field exercises the pinned singleton.
      if (!managerBound)
        manager.setDelegate(nullptr);
      Parameter *result = nullptr;
      if (test == "field-get")
        result = field.getParam();
      else {
        field.lookupParameters();
        result = field.cachedParameter();
      }
      manager.setDelegate(&delegate);
      const auto output =
          std::find(std::begin(parameters), std::end(parameters), result) -
          std::begin(parameters);
      std::cout << output << ' ' << field.elementState().dirty << ' '
                << (calls.empty() ? "-" : calls) << '\n';
      if (!managerBound) {
        FieldElement unbound("panel/level", nullptr);
        if (unbound.getParam() != nullptr)
          return 7;
      }
    }
  } else if (test == "text-string") {
    while (std::cin >> bound >> token) {
      presonus::panel::portable::TextEntryState state;
      state.text.fill(static_cast<char>(0xb7));
      delegate.result = bound ? &first : nullptr;
      FieldElement field("panel/level", &manager);
      field.setRefreshParameter(true);
      TextEntryElement element(state, field);
      const auto value = fromHex(token);
      calls.clear();
      element.setString(token == "~" ? nullptr : value.c_str());
      if (calls != (bound ? "dad" : "d"))
        return 6;
      const auto local =
          bound ? std::string_view(state.text.data(), state.text.size())
                : std::string_view(state.text.data());
      char attached[80]{};
      first.toString(attached, sizeof attached);
      std::cout << state.dirty << ' ' << toHex(local) << ' '
                << (bound ? toHex(attached) : "-") << '\n';
    }
  } else if (test == "field-destruction") {
    while (std::cin >> variant >> bound) {
      delegate.result = bound ? &first : nullptr;
      disposalResult = -1;
      if (variant == 0) {
        mapNextAllocation = true;
      } else {
        mappedReceiver = mmap(nullptr, 4096, PROT_READ | PROT_WRITE,
                              MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (mappedReceiver == MAP_FAILED)
          return 3;
      }
      FieldElement *field = variant == 0
                                ? new FieldElement("panel/level", &manager)
                                : ::new (mappedReceiver)
                                      FieldElement("panel/level", &manager);
      field->lookupParameters();
      calls.clear();
      if (variant == 0)
        destroy(field);
      else if (variant == 1)
        field->~FieldElement();
      else
        fieldBaseDestructor(field);

      const bool removed = calls == "r";
      unsigned char residence;
      errno = 0;
      const int result = mincore(mappedReceiver, 4096, &residence);
      if (variant == 0) {
        if (disposalResult != 0 || result != -1 || errno != ENOMEM)
          return 4;
      } else if (disposalResult != -1 || result != 0 ||
                 munmap(mappedReceiver, 4096) != 0) {
        return 5;
      }
      std::cout << (variant == 0) << ' ' << removed << '\n';
      mappedReceiver = nullptr;
    }
  } else {
    return 2;
  }
}
