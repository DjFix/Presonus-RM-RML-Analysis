#include "presonus/panel/FieldElement.hpp"
#include "presonus/panel/LCDManager.hpp"
#include "presonus/panel/TextEntryElement.hpp"

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <string_view>

using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Core::Portable::StringParam;
using Presonus::Panel::FieldElement;
using Presonus::Panel::ILCDDelegate;
using Presonus::Panel::LCDManager;
using Presonus::Panel::TextEntryElement;

namespace {
class Delegate final : public ILCDDelegate {
public:
  mutable unsigned lookups = 0;
  Parameter *result = nullptr;

  Parameter *lookupElementParameter(const char *name) const override {
    if (std::string_view(name) != "panel/level")
      std::abort();
    ++lookups;
    return result;
  }
};
} // namespace

int main() {
  const ParamInfo info{};
  StringParam first(info), cached(info), replacement(info), encoder(info);
  Parameter *parameters[] = {nullptr, &first, &cached, &replacement};
  Delegate delegate;
  LCDManager manager(LCDManager::SourcePortConstruction{});
  manager.setDelegate(&delegate);
  TextEntryElement::setEncoderParam(&encoder);
  presonus::panel::portable::TextEntryState state;
  TextEntryElement withoutField(state);
  if (withoutField.getInternalParam() || withoutField.getParam() != &encoder)
    return 3;

  unsigned initial, next;
  bool refresh;
  while (std::cin >> initial >> refresh >> next) {
    if (initial >= std::size(parameters) || next >= std::size(parameters))
      return 4;
    FieldElement field("panel/level", &manager);
    if (initial) {
      delegate.result = parameters[initial];
      if (field.getParam() != parameters[initial])
        return 5;
    }
    field.setRefreshParameter(refresh);
    delegate.result = parameters[next];
    delegate.lookups = 0;
    TextEntryElement text(state, field);
    const auto *result = text.getInternalParam();
    const auto id =
        std::find(std::begin(parameters), std::end(parameters), result) -
        std::begin(parameters);
    if (static_cast<unsigned>(id) >= std::size(parameters) ||
        field.cachedParameter() != result || text.getParam() != &encoder)
      return 6;
    std::cout << id << ' ' << delegate.lookups << '\n';
  }
  TextEntryElement::setEncoderParam(nullptr);
}
