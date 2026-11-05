#include "core/portable/corefile.h"
#include "core/portable/corepersistence.h"
#include "presonus/StormMuteGroupComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/PermissionsComponent.hpp"
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
using namespace Core::Portable;
namespace {
std::vector<std::string> events;
struct ClockCapture {
  bool active = false;
  bool failed = false;
  std::vector<std::int64_t> milliseconds;
  std::size_t consumed = 0;
};
thread_local ClockCapture clockCapture;

struct String : StringParam {
  using StringParam::StringParam;
  bool record = false;
  void fromString(const char *s, bool edit) override {
    if (record) {
      std::ostringstream out;
      out << "[\"from\"," << std::quoted(s ? s : "") << ',' << int(edit) << ']';
      events.push_back(out.str());
    }
    StringParam::fromString(s, edit);
  }
  void resetValue(bool edit) override {
    if (record)
      events.push_back("[\"reset\"," + std::to_string(edit) + "]");
    // Avoid recording internal provider implementation's virtual fromString.
    const bool saved = record;
    record = false;
    StringParam::resetValue(edit);
    record = saved;
  }
};
struct Observer : Component {
  Parameter *other = nullptr;
  void paramChanged(Parameter *p, int msg) override {
    if (msg == Parameter::kChanged || msg == Parameter::kRangeChanged)
      events.push_back(std::string("[\"") +
                       (msg == Parameter::kChanged ? "changed" : "range") +
                       "\"," + std::to_string(p == other) + "]");
  }
};
struct Tree : Component {
  void addBorrowed(Parameter *p) { paramList.add(p); }
  void detachBorrowed(Parameter *p) { paramList.remove(p); }
};
struct Services : presonus::storm_mute_port::Services {
  void refreshSip() override { throw std::logic_error("unexpected service"); }
  void activate(unsigned int) override {
    throw std::logic_error("unexpected service");
  }
  Component *connectedClient() override {
    throw std::logic_error("unexpected service");
  }
  void muteGroupStored(int) override {
    throw std::logic_error("unexpected service");
  }
  bool load(presonus::storm_mute_port::Group &) override {
    throw std::logic_error("unexpected service");
  }
};
void emitEvents() {
  std::cout << ",\"events\":[";
  for (size_t i = 0; i < events.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << events[i];
  }
  std::cout << ']';
}
} // namespace
// Test-only linker boundary. Production clock/time conversion stays in pinned
// CCL. Every call outside the one scoped idle execution reaches libc unchanged.
extern "C" int __real_clock_gettime(clockid_t, timespec *);
extern "C" int __wrap_clock_gettime(clockid_t id, timespec *time) {
  if (!clockCapture.active)
    return __real_clock_gettime(id, time);
  if (id != CLOCK_MONOTONIC || !time ||
      clockCapture.consumed >= clockCapture.milliseconds.size()) {
    clockCapture.failed = true;
    if (time)
      *time = {};
    return -1;
  }
  const auto ms = clockCapture.milliseconds[clockCapture.consumed++];
  time->tv_sec = static_cast<time_t>(ms / 1000);
  time->tv_nsec = static_cast<long>((ms % 1000) * 1000000);
  events.push_back("[\"clock\"," + std::to_string(ms) + "]");
  return 0;
}
int main(int argc, char **argv) {
  try {
    if (argc < 2)
      return 2;
    const std::string mode = argv[1];
    Presonus::Mixer::PermissionsBindings bindings;
    Presonus::Mixer::PermissionsComponent permissions(bindings);
    if (mode == "storm_01" || mode == "storm_02" || mode == "storm_03") {
      Services services;
      presonus::storm_mute_port::State state(services);
      std::array<presonus::mute_group_port::State, 9> memberStates;
      std::vector<std::unique_ptr<presonus::storm_mute_port::Group>> groups;
      for (int i = 0; i < 9; ++i) {
        groups.push_back(std::make_unique<presonus::storm_mute_port::Group>(
            memberStates[i]));
        if (i < 8)
          state.groups.add(groups.back().get());
        else
          state.allGroup = groups.back().get();
      }
      Presonus::StormMuteGroupComponent component(state);
      if (mode == "storm_01") {
        const auto v = std::stoull(argv[2]);
        component.setDelegate(
            reinterpret_cast<Presonus::StormMuteGroupComponent::Delegate *>(
                static_cast<uintptr_t>(v)));
        std::cout << "{\"pointer\":"
                  << reinterpret_cast<uintptr_t>(state.delegate) << "}\n";
      } else if (mode == "storm_02")
        std::cout << "{\"return\":"
                  << component.getSwitchTag(
                         static_cast<unsigned int>(std::stoull(argv[2])))
                  << "}\n";
      else {
        const ParamInfo info = PARAM_STRING(1, "probe", 0);
        String a(info), b(info), c(info);
        auto ptr = [&](unsigned int token) -> Parameter * {
          return token == 0    ? nullptr
                 : token == 11 ? &a
                 : token == 22 ? &b
                               : &c;
        };
        const unsigned int needle = std::stoul(argv[2]);
        for (int i = 0; i < 9; ++i) {
          std::istringstream in(argv[3 + i]);
          unsigned int token;
          while (in >> token)
            memberStates[i].members.add(ptr(token));
        }
        std::cout << "{\"return\":"
                  << int(component.isParamInAnyMuteGroup(ptr(needle))) << "}\n";
      }
      return 0;
    }
    if (mode == "w03_05") {
      const auto v = std::stoull(argv[2]);
      bindings.selectedSnapshot =
          reinterpret_cast<const Presonus::UC::ClientSubscription *>(
              static_cast<uintptr_t>(v));
      std::cout << "{\"return\":"
                << reinterpret_cast<uintptr_t>(permissions.getSelectedDevice())
                << "}\n";
      return 0;
    }
    Tree tree;
    const ParamInfo mixInfo =
        PARAM_FLOAT(0, "mix", -1, 1, 0, 1, nullptr, nullptr, 0, 0);
    const ParamInfo otherInfo =
        PARAM_FLOAT(1, "other", -1, 1, 0, 1, nullptr, nullptr, 0, 0);
    const ParamInfo stringInfo = PARAM_STRING(2, "mixText", 0);
    const ParamInfo codeInfo = PARAM_STRING(4, "code", 0);
    NumericParam mix(mixInfo), other(otherInfo);
    String target(stringInfo), code(codeInfo);
    struct Detach {
      Tree &tree;
      Parameter *a;
      Parameter *b;
      ~Detach() {
        tree.detachBorrowed(a);
        tree.detachBorrowed(b);
      }
    } detach{tree, &target, &code};
    bindings.mix = &mix;
    bindings.other = &other;
    bindings.accessCodeParameters = &tree;
    if (mode == "w03_02") {
      if (std::stoi(argv[2]))
        tree.addBorrowed(&target);
      target.fromString("initial", false);
      target.record = true;
      mix.setValue(std::stof(argv[3]), false);
      permissions.syncMixStrings();
      std::cout << "{\"text\":" << std::quoted(target.getText().str());
      emitEvents();
      std::cout << "}\n";
    } else if (mode == "w03_03") {
      Observer observer;
      observer.other = &other;
      mix.addObserver(&observer);
      other.addObserver(&observer);
      bindings.dirty = std::stoi(argv[2]);
      bindings.deadlineMilliseconds = std::stoll(argv[3]);
      const int expectedClocks = std::stoi(argv[6]);
      if (expectedClocks == 2)
        clockCapture.milliseconds = {std::stoll(argv[4]), std::stoll(argv[5])};
      else if (expectedClocks == 1)
        clockCapture.milliseconds = {std::stoll(argv[5])};
      else if (expectedClocks != 0)
        throw std::runtime_error("unexpected clock count input");
      struct ScopeClock {
        ScopeClock() { clockCapture.active = true; }
        ~ScopeClock() { clockCapture.active = false; }
      };
      {
        ScopeClock scoped;
        permissions.onIdle();
      }
      if (clockCapture.failed ||
          clockCapture.consumed != clockCapture.milliseconds.size())
        throw std::runtime_error("actual onIdle clock call count/id mismatch");
      std::cout << "{\"deadline\":" << bindings.deadlineMilliseconds
                << ",\"dirty\":" << int(bindings.dirty)
                << ",\"clock_calls\":" << clockCapture.consumed;
      emitEvents();
      std::cout << "}\n";
      mix.removeObserver(&observer);
      other.removeObserver(&observer);
    } else {
      Presonus::Mixer::MixerComponentBase mixer;
      bindings.mixer = &mixer;
      std::filesystem::create_directories(argv[2]);
      mixer.applicationDataRoot = argv[2];
      mixer.deviceDataFolder = "device";
      if (mode == "existing_helper") {
        Core::CStringBuffer<64> name(argv[4]);
        bindings.selectedName = std::stoi(argv[3]) ? &name : nullptr;
        FileName path("keep");
        permissions.getSelectedFileName(path);
        std::cout << "{\"filename\":" << std::quoted(path.str())
                  << ",\"dirty\":" << int(bindings.dirty) << "}\n";
      } else if (mode == "w03_04") {
        Core::CStringBuffer<64> name(argv[3]);
        FileName path;
        permissions.getFileName(path, name);
        std::cout << "{\"filename\":" << std::quoted(path.str()) << "}\n";
      } else if (mode == "w03_01") {
        if (std::stoi(argv[3]))
          tree.addBorrowed(&code);
        code.setDefaultText("default");
        code.fromString("initial", false);
        code.record = true;
        FileName path;
        permissions.getAccessCodeFileName(path);
        if (std::stoi(argv[4])) {
          Attributes attributes(AttributeAllocator::getDefault());
          int kind = std::stoi(argv[5]);
          if (kind == 1)
            attributes.set("code", 7);
          else if (kind == 2)
            attributes.set("code", argv[6]);
          if (!ArchiveUtils::saveToFile(path.str(), attributes))
            throw std::runtime_error("fixture file write failed");
        }
        permissions.loadAccessCode();
        std::cout << "{\"text\":" << std::quoted(code.getText().str());
        emitEvents();
        std::cout << "}\n";
      } else if (mode == "w03_06") {
        const ParamInfo infos[] = {
            PARAM_STRING(7, "persisted", ParamInfo::kStorable)};
        tree.addParameters(infos, 1);
        tree.getParameterByTag(7)->fromString("stored-value", false);
        Core::CStringBuffer<64> name(argv[4]);
        bindings.selectedName = &name;
        bindings.selectedSnapshot =
            std::stoi(argv[3])
                ? reinterpret_cast<const Presonus::UC::ClientSubscription *>(
                      &tree)
                : nullptr;
        FileName path;
        permissions.getSelectedFileName(path);
        permissions.saveSelectedDevice();
        auto &manager = FileIOManager::instance();
        if (bindings.selectedSnapshot) {
          bool observed = false;
          for (int i = 0; i < 1000; ++i) {
            manager.idle();
            Attributes written(AttributeAllocator::getDefault());
            if (ArchiveUtils::loadFromFile(written, path.str())) {
              auto *value = written.lookup("persisted");
              if (value && value->getString() &&
                  std::string(value->getString()) == "stored-value") {
                observed = true;
                break;
              }
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
          }
          if (!observed)
            throw std::runtime_error("background archive observation timeout");
        }
        manager.terminate();
        if (bindings.selectedSnapshot) {
          Attributes attributes(AttributeAllocator::getDefault());
          if (!ArchiveUtils::loadFromFile(attributes, path.str()))
            throw std::runtime_error("actual archive missing");
          auto *v = attributes.lookup("persisted");
          if (!v || std::string(v->getString()) != "stored-value")
            throw std::runtime_error("actual saved parameter mismatch");
          std::cout << "{\"saved\":true,\"filename\":"
                    << std::quoted(path.str()) << "}\n";
        } else
          std::cout << "{}\n";
      } else
        return 3;
    }
    // ParameterSet owns added parameters: release borrowed stack fixtures
    // before provider Component destruction.
    tree.detachBorrowed(&target);
    tree.detachBorrowed(&code);
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
