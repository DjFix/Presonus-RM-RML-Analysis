#include "presonus/uc/server.hpp"
#include <array>
#include <iostream>
#include <memory>
#include <string>

using namespace Presonus::UC;
using presonus::uc::AvailableServerView;
using presonus::uc::ServerRegistrarState;
using Views = Core::Vector<AvailableServerView *>;

static void printRoster(const Views &views) {
  for (int i = 0; i < views.count(); ++i)
    std::cout << ' ' << views.at(i)->identifier;
  std::cout << '\n';
}

class Listener : public INetworkListener {
public:
  Listener(int number, const Views &views) : number_(number), views_(views) {}

  void onServerAvailable(int id, const ServerInfo &) override {
    record("added", id);
  }
  void onServerUnavailable(int id) override { record("removed", id); }
  void onServerChanged(int id) override { record("changed", id); }

private:
  void record(const char *event, int id) const {
    std::cout << event << ' ' << number_ << ' ' << id;
    printRoster(views_);
  }
  int number_;
  const Views &views_;
};

class TrackedRemote : public RemoteServer {
public:
  explicit TrackedRemote(int id) : id_(id) {}
  ~TrackedRemote() override {
    if (observed_) {
      std::cout << "destructor 0 " << id_;
      printRoster(*observed_);
      deleting_ = id_;
    }
  }

  static void operator delete(void *pointer) noexcept {
    if (observed_) {
      std::cout << "delete 0 " << deleting_;
      printRoster(*observed_);
    }
    ::operator delete(pointer);
  }

  static const Views *observed_;

private:
  static int deleting_;
  int id_;
};

const Views *TrackedRemote::observed_ = nullptr;
int TrackedRemote::deleting_ = 0;

int main(int argc, char **argv) {
  if (argc < 7)
    return 1;
  const std::string mode = argv[1];
  const bool local = mode == "add_local" || mode == "remove_local";
  const bool manual = mode == "remove_manual";
  const int listenerCount = std::stoi(argv[4]);
  const bool full = std::stoi(argv[5]) != 0;
  const bool nullAddress = std::stoi(argv[6]) != 0;
  constexpr std::array addresses = {"desk", "desk",  "desk",
                                    "desk", "other", ""};
  constexpr std::array<unsigned short, 6> ports = {123, 123, 123,
                                                   124, 123, 65535};
  std::array<presonus::uc::ServerState, 6> localStates;
  std::array<std::unique_ptr<LocalServer>, 6> locals;
  std::array<std::unique_ptr<TrackedRemote>, 6> remotes;
  std::array<AvailableServerView, 6> views;
  AvailableServerView other;
  ServerRegistrarState borrowed;
  auto registrar = manual ? std::make_unique<ServerRegistrar>()
                          : std::make_unique<ServerRegistrar>(borrowed);
  auto &state = registrar->sourcePortState();
  auto &selected = local ? state.localServers : state.remoteServers;
  auto &untouched = local ? state.remoteServers : state.localServers;
  for (int i = 0; i < 6; ++i) {
    auto &view = views[i];
    view.identifier = i + 1;
    view.remoteAddress = addresses[i];
    view.remotePort = ports[i];
    view.manuallyAdded = i != 1;
    if (local) {
      locals[i] = std::make_unique<LocalServer>(
          presonus::uc::ServerSourcePortTag{}, localStates[i]);
      view.localIdentity = locals[i].get();
      view.identity = locals[i].get();
    } else {
      remotes[i] = std::make_unique<TrackedRemote>(i + 1);
      view.identity = remotes[i].get();
    }
    if (!manual && !state.allServerViews.add(&view))
      return 2;
  }
  other.identifier = 5;
  if (!untouched.add(&other))
    return 3;
  const int initialCount = argc - 7;
  selected.setDelta(1);
  if (!selected.resize(full ? initialCount : 8))
    return 4;
  for (int i = 7; i < argc; ++i) {
    const int at = std::stoi(argv[i]) - 1;
    if (manual) {
      if (!registrar->sourcePortAddOwnedRemote(remotes[at].get(), views[at]))
        return 5;
      remotes[at].release();
    } else if (!selected.add(&views[at]))
      return 6;
  }

  Listener first(1, selected), second(2, selected);
  if ((listenerCount > 0 && !state.listeners.add(&first)) ||
      (listenerCount > 1 && !state.listeners.add(&second)))
    return 7;
  if (manual) {
    TrackedRemote::observed_ = &selected;
    registrar->removeManuallyAdded(
        nullAddress ? nullptr : argv[2],
        static_cast<unsigned short>(std::stoi(argv[3])));
    TrackedRemote::observed_ = nullptr;
    for (auto &view : views) {
      if (selected.contains(&view) != state.allServerViews.contains(&view))
        return 8;
    }
  } else {
    const int at = std::stoi(argv[2]) - 1;
    if (mode == "add_local")
      registrar->add(locals[at].get());
    else if (mode == "add_remote")
      registrar->add(remotes[at].get());
    else if (mode == "remove_local")
      registrar->remove(locals[at].get());
    else if (mode == "remove_remote")
      registrar->remove(remotes[at].get());
    else
      return 9;
  }
  if (untouched.count() != 1 || untouched.at(0) != &other)
    return 10;
  std::cout << "final";
  printRoster(selected);
}
