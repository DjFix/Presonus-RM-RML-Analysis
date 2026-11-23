#include "presonus/panel/LCDManager.hpp"

#include <iostream>
#include <string_view>

using Presonus::Panel::Book;
using Presonus::Panel::ILCDDelegate;
using Presonus::Panel::LCDComponent;
using Presonus::Panel::LCDManager;
using Presonus::Panel::MixerLCD;
using presonus::panel::portable::makeMixerLCDLookupDelegate;

namespace {
class AbstractDelegate final : public ILCDDelegate {
public:
  Core::Portable::Parameter *
  lookupElementParameter(const char *) const override {
    ++lookupCalls;
    return nullptr;
  }
  Book *getDefaultBook() const override {
    ++calls;
    return result;
  }
  Book *result = nullptr;
  mutable unsigned calls = 0;
  mutable unsigned lookupCalls = 0;
};

class LegacyDelegate final : public ILCDDelegate {
public:
  Core::Portable::Parameter *
  lookupElementParameter(const char *) const override {
    ++calls;
    return nullptr;
  }
  mutable unsigned calls = 0;
};

class ExistingBookCommands final : public presonus::panel::portable::Book {
public:
  void command(unsigned slot) override { observed = slot; }
  unsigned observed = 0;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const bool rm = std::string_view(argv[1]) == "server";
  const std::string_view scenario = argv[2];
  LCDManager manager(LCDManager::SourcePortConstruction{});
  const LCDManager &reader = manager;
  LegacyDelegate legacy;
  manager.setDelegate(&legacy);
  if (reader.getDefaultBook() || reader.lookupElementParameter("legacy") ||
      legacy.calls != 1)
    return 1;

  const bool match = scenario == "matching-tag";
  const bool bound = scenario != "null-delegate";
  Book first(12), second(match ? 11 : 13);
  Book *found = nullptr;
  if (rm) {
    LCDComponent lcd;
    Book *slots[] = {&first, &second};
    lcd.bindBooks(
        LCDComponent::Books(slots, scenario == "empty-roster" ? 0 : 2));
    lcd.bindCurrentBook(&first);
    ExistingBookCommands commands;
    presonus::panel::portable::State state{commands};
    MixerLCD mixer(state);
    auto delegate = makeMixerLCDLookupDelegate(mixer, lcd);
    auto legacyMixer = makeMixerLCDLookupDelegate(mixer);
    if (legacyMixer.getDefaultBook())
      return 1;
    manager.setDelegate(bound ? &delegate : nullptr);
    found = reader.getDefaultBook();
    mixer.next();
    if (commands.observed != 0x28 || lcd.getBook() != &first)
      return 1;
    manager.setDelegate(nullptr);
  } else {
    AbstractDelegate delegate;
    delegate.result = match ? &second : nullptr;
    manager.setDelegate(bound ? &delegate : nullptr);
    found = reader.getDefaultBook();
    if (delegate.calls != static_cast<unsigned>(bound) || delegate.lookupCalls)
      return 1;
    manager.setDelegate(nullptr);
  }
  if (found != (match ? &second : nullptr) || reader.getDefaultBook())
    return 1;
  std::cout << (found ? 1 : 0) << '\n';
}
