#include "core/portable/corepersistence.h"
#include "presonus/LinkableComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/PermissionsComponent.hpp"
#include "presonus/uc/ClientSubscription.hpp"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <vector>
using namespace Core::Portable;
namespace {
struct Tree : Component {
  void attach(Parameter *p) { paramList.add(p); }
  void detach(Parameter *p) { paramList.remove(p); }
};
struct Boundary : Presonus::linkable_port::Boundary {
  Presonus::LinkableComponent *query(Presonus::LinkableComponent &,
                                     std::uint32_t) override {
    throw std::logic_error("query");
  }
  void remove(Presonus::LinkableComponent &) override {
    throw std::logic_error("remove");
  }
  void set(Presonus::LinkableComponent &, Presonus::LinkableComponent &,
           bool) override {
    throw std::logic_error("set");
  }
  void master(Presonus::LinkableComponent &,
              Presonus::LinkableComponent &) override {
    throw std::logic_error("master");
  }
};
struct Observer : Component {
  Parameter *mix = nullptr, *other = nullptr;
  std::vector<std::pair<std::string, std::string>> events;
  void paramChanged(Parameter *p, int msg) override {
    if (msg == Parameter::kChanged || msg == Parameter::kRangeChanged)
      events.emplace_back(p == mix     ? "mix"
                          : p == other ? "other"
                                       : "saved",
                          msg == Parameter::kChanged ? "changed" : "range");
  }
};
void strings(const ListParam &p) {
  std::cout << '[';
  for (int i = 0; i < p.getStringCount(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << std::quoted(p.getStringAt(i));
  }
  std::cout << ']';
}
} // namespace
int main(int argc, char **argv) {
  try {
    if (argc != 14)
      return 2;
    const int op = std::stoi(argv[1]), old = std::stoi(argv[4]);
    const ParamInfo mi = {
        ParamInfo::kList,     0,       "mix",   0,       -1,      0,      0, 1,
        ParamInfo::kStorable, nullptr, nullptr, nullptr, nullptr, nullptr};
    const ParamInfo oi = {
        ParamInfo::kList,     1,       "other", 0,       -1,      0,      0, 1,
        ParamInfo::kStorable, nullptr, nullptr, nullptr, nullptr, nullptr};
    const ParamInfo ti = PARAM_STRING(2, "mixText", ParamInfo::kStorable);
    ListParam mix(mi), other(oi);
    StringParam saved(ti);
    Tree tree;
    tree.attach(&mix);
    tree.attach(&other);
    tree.attach(&saved);
    struct Detach {
      Tree &t;
      Parameter *a, *b, *c;
      ~Detach() {
        t.detach(a);
        t.detach(b);
        t.detach(c);
      }
    } detach{tree, &mix, &other, &saved};
    for (int i = 0; i < old; ++i)
      mix.appendString(("seed" + std::to_string(i)).c_str());
    mix.setValue(std::stof(argv[5]), false);
    other.appendString("oldOther");
    saved.setDefaultText("default");
    saved.fromString("initial", false);
    Presonus::Mixer::MixerComponentBase mixer;
    Presonus::Mixer::PermissionsBindings b;
    b.mixer = &mixer;
    b.mix = &mix;
    b.other = &other;
    b.mixList = std::stoi(argv[8]) ? &mix : nullptr;
    b.otherList = &other;
    b.accessCodeParameters = &tree;
    b.dirty = std::stoi(argv[6]);
    b.loading = std::stoi(argv[7]);
    b.defaultPermissions = std::stoi(argv[9]);
    const Core::CStringBuffer<64> app(argv[2]), empty;
    Presonus::UC::ClientSubscription client(
        Presonus::UC::ClientSubscription::SourcePortValues{}, app, empty,
        empty);
    b.selectedSnapshot = std::string(argv[2]) == "null" ? nullptr : &client;
    Boundary boundary;
    std::vector<std::unique_ptr<Presonus::linkable_port::State>> states;
    std::vector<std::unique_ptr<Presonus::LinkableComponent>> links;
    std::vector<std::unique_ptr<int>> tokens;
    std::vector<std::pair<Presonus::Mixer::ChannelComponent *,
                          Presonus::Mixer::PermissionsAuxView>>
        views;
    std::istringstream channels(argv[3]);
    std::string token;
    while (std::getline(channels, token, ';')) {
      if (token == "null") {
        mixer.mixChannels.add(nullptr);
        continue;
      }
      auto colon = token.find(':');
      const auto number =
          static_cast<std::uint32_t>(std::stoull(token.substr(0, colon)));
      const bool linked = std::stoi(token.substr(colon + 1));
      states.push_back(std::make_unique<Presonus::linkable_port::State>());
      links.push_back(std::make_unique<Presonus::LinkableComponent>(
          *states.back(), boundary));
      if (linked)
        states.back()->partner = links.back().get();
      // Opaque identity token: never dereferenced as ChannelComponent; the
      // typed projection below returns an actual canonical LinkableComponent
      // object.
      tokens.push_back(std::make_unique<int>(0));
      auto *channel = reinterpret_cast<Presonus::Mixer::ChannelComponent *>(
          tokens.back().get());
      mixer.mixChannels.add(channel);
      views.emplace_back(channel, Presonus::Mixer::PermissionsAuxView{
                                      links.back().get(), number});
    }
    b.auxView = [&](const Presonus::Mixer::ChannelComponent *c) {
      for (const auto &v : views)
        if (v.first == c)
          return v.second;
      throw std::logic_error("unbound channel");
    };
    const std::string kind(argv[10]);
    Core::CStringBuffer<64> name(kind == "empty" ? "" : "client");
    b.selectedName = &name;
    const std::filesystem::path work(argv[13]);
    std::filesystem::create_directories(work);
    mixer.applicationDataRoot = work.c_str();
    mixer.deviceDataFolder = "device";
    Presonus::Mixer::PermissionsComponent permissions(b);
    FileName filename;
    permissions.getSelectedFileName(filename);
    if (op == 3 && kind != "empty") {
      if (std::filesystem::exists(filename.str()))
        throw std::logic_error("fixture path must be fresh");
      if (kind == "invalid") {
        std::ofstream f(filename.str());
        f << "not a JSON archive";
      } else if (kind != "absent") {
        Attributes a(AttributeAllocator::getDefault());
        if (kind != "missing")
          a.set("mixText", argv[11]);
        if (kind == "other")
          a.set("other", 1);
        if (!ArchiveUtils::saveToFile(filename.str(), a))
          throw std::runtime_error("write archive");
      }
    }
    Observer observer;
    observer.mix = &mix;
    observer.other = &other;
    mix.addObserver(&observer);
    other.addObserver(&observer);
    saved.addObserver(&observer);
    const ParamInfo ni =
        PARAM_FLOAT(99, "numeric", -10, 10, 0, 1, nullptr, nullptr, 0, 0);
    NumericParam numeric(ni);
    if (op == 4) {
      numeric.setValue(std::stof(argv[12]), false);
      b.mix = &numeric;
      permissions.syncMixStrings();
    } else if (op == 1)
      permissions.updateOtherPermissionsStrings();
    else if (op == 2)
      permissions.updateMixPermissionsStrings();
    else if (op == 3)
      permissions.loadSelectedDevice();
    else
      return 3;
    mix.removeObserver(&observer);
    other.removeObserver(&observer);
    saved.removeObserver(&observer);
    std::cout << "{\"mix\":";
    strings(mix);
    std::cout << ",\"other\":";
    strings(other);
    std::cout << ",\"mixValue\":" << mix.getValue()
              << ",\"otherValue\":" << other.getValue()
              << ",\"max\":" << mix.getMax() << ",\"dirty\":" << int(b.dirty)
              << ",\"loading\":" << int(b.loading)
              << ",\"saved\":" << std::quoted(saved.getText().str())
              << ",\"events\":[";
    bool first = true;
    for (const auto &e : observer.events) {
      if (!first)
        std::cout << ',';
      first = false;
      std::cout << '[' << std::quoted(e.first) << ',' << std::quoted(e.second)
                << ']';
    }
    std::cout << "]}\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
