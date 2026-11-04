#include "core/public/corestringbuffer.h"
#include "presonus/IMainScreenPageController.hpp"
#include "presonus/MappingTable.hpp"
#include "presonus/panel/control.hpp"
#include <cstring>
namespace Presonus {
int MappingTable::Item::translateMode(const char *name) {
  struct Mode {
    const char *name;
    int value;
  };
  static constexpr Mode modes[] = {
      {"meter-audio", 0},       {"meter-audio-reverse", 1},
      {"meter-centered", 2},    {"meter-stereobar", 3},
      {"meter-single-seg", 4},  {"meter-single-reverse", 5},
      {"meter-disabled-h", 6},  {"meter-disabled-v", 7},
      {"meter-bar", 8},         {"meter-audio-no-taper", 11},
      {"meter-bar-reverse", 9}, {"meter-bar-upsidedown", 10},
      {"meter-raw", 12},        {"meter-audio-lineardb", 13}};
  if (name)
    for (const auto &m : modes)
      if (std::strcmp(name, m.name) == 0)
        return m.value;
  return 0;
}
void MappingTable::connect(const char *name,
                           Core::Portable::Parameter *parameter,
                           const char *mode, bool force) {
  force = force || parameter == nullptr;
  if (auto *item = findItem(name ? name : "")) {
    // The native app issues setOriginal even for a null alias. Pinned CCL's
    // member implementation requires a live object; guard that provider call
    // as an intentional source-port adaptation while retaining app dispatch.
    auto *alias = item->alias;
    if (alias)
      alias->setOriginal(parameter);
    auto *control = item->control;
    if (!control || (!mode && !force))
      return;
    int translated = Item::translateMode(mode);
    if (control->getParameter() != alias ||
        control->getParameterMode() != translated)
      control->setParameter(alias, translated);
    else if (force) {
      if (alias)
        control->paramChanged(alias, 3);
      else
        control->broadcastValue(0);
    }
    return;
  }
  const char *value = name ? name : "";
  if (std::strstr(value, "page:") != value)
    return;
  const char *dot = std::strchr(value, '.');
  if (!dot || dot <= value)
    return;
  Core::CStringBuffer<32> page(value + 5);
  int index = static_cast<int>(dot - value) - 5;
  if (index >= 0 && index < static_cast<int>(std::strlen(page.str())))
    page.truncate(index);
  Core::CStringBuffer<32> param(dot + 1);
  if (auto *controller = findPage(page.str()))
    controller->connectParameter(param.str(), parameter);
}
} // namespace Presonus
