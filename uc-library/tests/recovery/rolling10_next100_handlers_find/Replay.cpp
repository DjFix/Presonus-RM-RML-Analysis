#include "presonus/surface/AssignmentHandlerTable.hpp"
#include "presonus/surface/DAWMixerHandler.hpp"
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
struct Dependencies final : presonus::surface::DAWMixerDependencies {
  Presonus::DAWChannel *focusChannel() override { throw 1; }
  Presonus::DAWChannel *mainChannel() override { throw 1; }
  int selectedMix() const override { throw 1; }
  bool showStripMeters() const override { throw 1; }
  Core::Portable::Component *component(Presonus::DAWChannel *) const override {
    throw 1;
  }
  Presonus::DAWDeviceFolder *folder(Presonus::DAWChannel *,
                                    bool) const override {
    throw 1;
  }
  int usedCount(Presonus::DAWDeviceFolder *) const override { throw 1; }
  Core::Portable::Component *slot(Presonus::DAWDeviceFolder *,
                                  int) const override {
    throw 1;
  }
  const char *channelType(Presonus::DAWChannel *) const override { throw 1; }
  void connect(const char *, Core::Portable::Parameter *, const char *,
               bool) override {
    throw 1;
  }
  void assignChannels() override { throw 1; }
  void assignControlLinkTargets() override { throw 1; }
  void assignSelectedChannelTargets() override { throw 1; }
  void assignFlexStrip() override { throw 1; }
};
std::string decode(const std::string &s) {
  std::string out;
  if (s == "-" || s == "." || s == "P")
    return out;
  for (std::size_t i = 0; i < s.size(); i += 2)
    out.push_back(static_cast<char>(std::stoi(s.substr(i, 2), nullptr, 16)));
  return out;
}
// Test-only abstract-interface fixture, never an original app implementation.
struct Handler final : Presonus::AssignmentHandler {
  std::string name;
  bool nullName;
  int index;
  std::vector<int> &calls;
  const Presonus::Surface::DAWMixerHandler *provider;
  Handler(std::string n, bool empty, int i, std::vector<int> &c,
          const Presonus::Surface::DAWMixerHandler *p)
      : name(std::move(n)), nullName(empty), index(i), calls(c), provider(p) {}
  const char *getName() const override {
    calls.push_back(index);
    return provider ? provider->getName() : nullName ? nullptr : name.c_str();
  }
  void updateConnections() override {
    throw std::logic_error("outside findHandler domain");
  }
};
int main(int argc, char **argv) {
  Dependencies dependencies;
  presonus::surface::DAWMixerState state;
  Core::Portable::ParamList automation;
  Presonus::Surface::DAWMixerHandler provider(dependencies, state, automation);
  if (argc == 2 && std::string(argv[1]) == "--observe-provider") {
    std::cout << provider.getName() << '\n';
    return 0;
  }
  std::string query;
  int count;
  while (std::cin >> query >> count) {
    std::vector<int> calls;
    std::vector<std::unique_ptr<Handler>> objects;
    Core::Vector<Presonus::AssignmentHandler *> handlers;
    for (int i = 0; i < count; ++i) {
      std::string name;
      std::cin >> name;
      objects.push_back(
          std::make_unique<Handler>(decode(name), name == "-", i, calls,
                                    name == "P" ? &provider : nullptr));
      handlers.add(objects.back().get());
    }
    Presonus::AssignmentHandlerTable table(handlers);
    auto text = decode(query);
    auto *result = table.findHandler(query == "-" ? nullptr : text.c_str());
    int found = -1;
    for (int i = 0; i < count; ++i)
      if (result == objects[i].get())
        found = i;
    std::cout << found << ' ' << calls.size();
    for (int i : calls)
      std::cout << ' ' << i;
    std::cout << '\n';
  }
}
