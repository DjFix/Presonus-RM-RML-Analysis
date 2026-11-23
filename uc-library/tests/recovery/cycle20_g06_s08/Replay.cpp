#include "core/portable/corecomponent.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/MixerLCD.hpp"
#include "presonus/panel/PanelRegistrar.hpp"

#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using Core::Portable::Component;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Presonus::Mixer::MixerComponentBase;
using Presonus::Panel::FrontPanelComponent;
using Presonus::Panel::MixerLCD;
using Presonus::Panel::PanelRegistrar;

struct BookCapture final : presonus::panel::portable::Book {
  std::vector<unsigned> operations;
  void command(unsigned slot) override { operations.push_back(slot); }
};

const Component *frontRoot = nullptr;
const Component *mixerRoot = nullptr;
const Component *calledRoot = nullptr;
std::string calledPath;
int calls = 0;
const char *incomingName = nullptr;
bool usedIncomingName = false;

std::string decode(const std::string &encoded) {
  if (encoded == "-") {
    return {};
  }
  std::string value;
  for (std::size_t i = 0; i < encoded.size(); i += 2) {
    value.push_back(
        static_cast<char>(std::stoi(encoded.substr(i, 2), nullptr, 16)));
  }
  return value;
}

void encode(const std::string &value) {
  static constexpr char hex[] = "0123456789abcdef";
  if (value.empty()) {
    std::cout << '-';
  }
  for (unsigned char c : value) {
    std::cout << hex[c >> 4] << hex[c & 15];
  }
}

constexpr ParamInfo frontFader =
    PARAM_INT_(6101, "fader", 0, 20, 7, "", "", 0, 0, "", nullptr);
constexpr ParamInfo mixerFader =
    PARAM_INT_(6201, "fader", 0, 20, 12, "", "", 0, 0, "", nullptr);
constexpr ParamInfo nestedFader =
    PARAM_INT_(6202, "fader", 0, 20, 15, "", "", 0, 0, "", nullptr);
} // namespace

extern "C" Parameter *realLookup(const Component *, const char *) asm(
    "__real__ZNK4Core8Portable9Component15lookupParameterEPKc");
extern "C" Parameter *observeLookup(const Component *, const char *) asm(
    "__wrap__ZNK4Core8Portable9Component15lookupParameterEPKc");

extern "C" Parameter *observeLookup(const Component *root, const char *path) {
  if (root != frontRoot && root != mixerRoot) {
    throw std::runtime_error("unexpected lookup root");
  }
  ++calls;
  calledRoot = root;
  calledPath = path;
  usedIncomingName = path == incomingName;
  return realLookup(root, path);
}

int main() {
  MixerComponentBase mixer;
  Component mixerParameters("mixer");
  mixerParameters.addParameters(&mixerFader, 1);
  auto *other = new Component("other");
  auto *nestedPanel = new Component("panel");
  nestedPanel->addParameters(&nestedFader, 1);
  other->addChild(nestedPanel);
  mixerParameters.addChild(other);
  presonus::panel_binding::PanelRegistrarPortState registrarState;
  PanelRegistrar registrar(registrarState);
  FrontPanelComponent front(mixer, registrar);
  auto &panelParameters = front.portableState().component;
  panelParameters.addParameters(&frontFader, 1);
  frontRoot = &panelParameters;
  mixerRoot = &mixerParameters;

  BookCapture book;
  presonus::panel::portable::State state{book};
  MixerLCD lcd(state);
  lcd.previous();
  lcd.next();
  lcd.up();
  lcd.down();
  lcd.store();
  if (book.operations != std::vector<unsigned>{0x2c, 0x28, 0x20, 0x24, 0x38}) {
    return 1;
  }
  try {
    static_cast<const MixerLCD &>(lcd).lookupElementParameter("fader");
    return 2;
  } catch (const std::logic_error &) {
  }
  try {
    lcd.bindLookupProviders(front, mixer);
    return 3;
  } catch (const std::invalid_argument &) {
  }
  mixer.childLookupParameters = &mixerParameters;
  lcd.bindLookupProviders(front, mixer);
  const MixerLCD &lookup = lcd;

  std::string prefixToken;
  std::string queryToken;
  while (std::cin >> prefixToken >> queryToken) {
    panelParameters.setName(decode(prefixToken).c_str());
    const auto query = decode(queryToken);
    calledRoot = nullptr;
    calledPath.clear();
    calls = 0;
    incomingName = query.c_str();
    Parameter *result = lookup.lookupElementParameter(incomingName);
    if (calls != 1 || result != realLookup(calledRoot, calledPath.c_str()) ||
        (result && result != panelParameters.getParameterByTag(6101) &&
         result != mixerParameters.getParameterByTag(6201) &&
         result != nestedPanel->getParameterByTag(6202))) {
      return 4;
    }
    std::cout << (calledRoot == frontRoot ? "front" : "mixer") << ' ';
    encode(calledPath);
    std::cout << ' ' << (result ? result->getTag() : 0) << ' '
              << usedIncomingName << '\n';
  }
  return book.operations.size() == 5 ? 0 : 5;
}
