#include "presonus/panel/FieldElement.hpp"
#include "presonus/panel/LCDManager.hpp"
#include "presonus/panel/TextEntryElement.hpp"

#include <cstdlib>
#include <iostream>
#include <string>
#include <string_view>

using Core::Portable::IParamObserver;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Core::Portable::StringParam;
using Presonus::Panel::FieldElement;
using Presonus::Panel::ILCDDelegate;
using Presonus::Panel::LCDManager;
using Presonus::Panel::TextEntryElement;

namespace {
std::string calls;
IParamObserver *observerSeen = nullptr;
Parameter *parameterSeen = nullptr;

class Delegate final : public ILCDDelegate {
public:
  Parameter *result = nullptr;
  std::string key;

  Parameter *lookupElementParameter(const char *name) const override {
    if (name != key)
      std::abort();
    calls.push_back('d');
    return result;
  }
};

class DelegateBinding {
public:
  explicit DelegateBinding(Delegate &delegate)
      : manager_(FieldElement::defaultLookupManager()) {
    manager_.setDelegate(&delegate);
  }
  ~DelegateBinding() { manager_.setDelegate(nullptr); }

private:
  LCDManager &manager_;
};

std::string unhex(std::string_view value) {
  if (value == "-")
    return {};
  constexpr std::string_view digits = "0123456789abcdef";
  std::string result;
  for (std::size_t i = 0; i < value.size(); i += 2)
    result += static_cast<char>((digits.find(value[i]) << 4) |
                                digits.find(value[i + 1]));
  return result;
}

bool showField(const FieldElement &field, const Parameter &provider) {
  const auto *parameter = field.cachedParameter();
  if ((parameter && (parameter != &provider || calls != "da")) ||
      (!parameter && calls != "d"))
    return false;
  const auto &state = field.elementState();
  std::cout << state.x << ' ' << state.y << ' ' << state.dirty << ' '
            << (parameter != nullptr) << ' ' << field.textBuffer().isEmpty();
  return true;
}
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

extern "C" void wrapAdd(Parameter *parameter, IParamObserver *observer) {
  if (observerSeen || parameterSeen)
    std::abort();
  realAdd(parameter, observer);
  observerSeen = observer;
  parameterSeen = parameter;
  calls.push_back('a');
}

extern "C" void wrapRemove(Parameter *parameter, IParamObserver *observer) {
  if (observer != observerSeen || parameter != parameterSeen)
    std::abort();
  realRemove(parameter, observer);
  observerSeen = nullptr;
  parameterSeen = nullptr;
  calls.push_back('r');
}

struct DerivedText : TextEntryElement {
  using TextEntryElement::TextEntryElement;
};

template <class T>
bool replayText(int x, int y, const std::string &key,
                const Parameter &provider) {
  const T text(x, y, key.c_str());
  if (!text.fieldElement() || !showField(*text.fieldElement(), provider))
    return false;
  const auto &state = text.textState();
  if (state.dirty != text.fieldElement()->needsToDraw())
    return false;
  std::cout << ' ' << state.cursor << ' ' << (state.text.front() == '\0')
            << '\n';
  return true;
}

int main() {
  const ParamInfo info{};
  StringParam provider(info);
  Delegate delegate;
  const DelegateBinding binding(delegate);
  int x, y;
  bool attached, base;
  std::string input;
  while (std::cin >> base >> x >> y >> attached >> input) {
    delegate.key = unhex(input);
    delegate.result = attached ? &provider : nullptr;
    calls.clear();
    const bool ok =
        base ? replayText<DerivedText>(x, y, delegate.key, provider)
             : replayText<TextEntryElement>(x, y, delegate.key, provider);
    if (!ok || calls != (attached ? "dar" : "d") || observerSeen ||
        parameterSeen)
      return 4;
  }
}
