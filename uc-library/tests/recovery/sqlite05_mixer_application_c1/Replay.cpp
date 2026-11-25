// Share the offline card harness and its actual allocator/provider observers.
#define main cardLifecycleReplayMain
#define __wrap__ZdlPv cardWrapDelete
#define __wrap__ZdlPvm cardWrapSizedDelete
// The provider branch returns explicitly. Renaming main also removes its
// implicit return for the other branches, which are unused here.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wreturn-type"
#include "../CardUCNetLifecycleReplay.cpp"
#pragma GCC diagnostic pop
#undef __wrap__ZdlPvm
#undef __wrap__ZdlPv
#undef main

#include "presonus/dsp/OMAPTargetHandler.hpp"
#include "presonus/mixer/setup_property_applications.hpp"
#include <signal.h>

using Presonus::Mixer::MixerApplication;
static void *applicationAddress;
static bool expectRegistration;

extern "C" void __wrap__ZdlPv(void *p) {
  if (capture && p == applicationAddress) {
    trace.push_back("APP_FREE");
    applicationAddress = nullptr;
  }
  cardWrapDelete(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  if (capture && p == applicationAddress) {
    trace.push_back("APP_FREE");
    applicationAddress = nullptr;
  }
  cardWrapSizedDelete(p, size);
}

extern "C" int __real_sigaction(int, const struct sigaction *,
                                struct sigaction *);
extern "C" int __wrap_sigaction(int signal, const struct sigaction *action,
                                struct sigaction *previous);

struct App final : MixerApplication {
  App() = default;
  App(presonus::mixer::SetupContextTag tag,
      const presonus::mixer::SetupContext &context)
      : MixerApplication(tag, context) {}
  ~App() override {
    if (capture)
      trace.push_back("DERIVED");
  }

  void onProgress(const char *, float) override { std::abort(); }
  ClientRootComponent *createClientComponent(const NetworkItem &) override {
    std::abort();
  }
  void releaseClientComponent(ClientRootComponent *) override { std::abort(); }
  NOAASetupProperty getNOAASetupProperty() const override { std::abort(); }

  using MixerApplication::adoptPortableCard;
  using MixerApplication::consumePortableQuitRequest;
  using MixerApplication::portableCurrentApplication;
  using MixerApplication::portableLifecycleDefaults;
  using MixerApplication::portableOMAPTarget;
  using MixerApplication::portableSetupContext;

  static void report(MixerApplication &app) {
    const auto &defaults = (app.*&App::portableLifecycleDefaults)();
    for (auto value : defaults.initialBytes)
      std::cout << ' ' << unsigned(value);
    for (auto value : defaults.initialWords)
      std::cout << ' ' << value;
    for (auto value : defaults.setupWords)
      std::cout << ' ' << value;
    for (auto value : defaults.targetWords)
      std::cout << ' ' << value;
  }
};

extern "C" int __wrap_sigaction(int signal, const struct sigaction *action,
                                struct sigaction *previous) {
  if (expectRegistration && action) {
    assert(signal == SIGINT && action->sa_handler != SIG_IGN &&
           action->sa_handler != SIG_DFL);
    auto *app = App::portableCurrentApplication();
    assert(app);
    std::cout << "REGISTER";
    App::report(*app);
    std::cout << '\n';
    expectRegistration = false;
  }
  return __real_sigaction(signal, action, previous);
}

static void restoreSignalTest() {
  struct sigaction action{};
  assert(sigaction(SIGINT, nullptr, &action) == 0);
  assert(action.sa_handler == SIG_IGN);
  assert(App::portableCurrentApplication() == nullptr);
}

static int constructors() {
  expectRegistration = true;
  {
    App app;
    assert(!expectRegistration && App::portableCurrentApplication() == &app);
    struct sigaction action{};
    assert(sigaction(SIGINT, nullptr, &action) == 0);
    assert(action.sa_handler != SIG_IGN && action.sa_handler != SIG_DFL);
    std::cout << "DEFAULTS";
    App::report(app);
    std::cout << '\n';
    std::cout << "INTERFACES "
              << (static_cast<void *>(static_cast<IFirmwareUpdateListener *>(
                      &app)) == static_cast<void *>(&app))
              << ' '
              << (static_cast<void *>(static_cast<INetworkClientFactory *>(
                      &app)) != static_cast<void *>(&app))
              << '\n';
    auto &target = app.portableOMAPTarget();
    Core::Property property(123, sizeof(Core::Property));
    target.getProperty(property);
    assert(property.type == 123 && property.size == sizeof(Core::Property));
    assert(!app.consumePortableQuitRequest());
    assert(raise(SIGINT) == 0);
    assert(app.consumePortableQuitRequest() &&
           !app.consumePortableQuitRequest());
    {
      App other;
      assert(App::portableCurrentApplication() == &other);
      assert(raise(SIGINT) == 0);
      assert(!app.consumePortableQuitRequest());
      assert(other.consumePortableQuitRequest());
    }
    assert(App::portableCurrentApplication() == &app);
  }
  restoreSignalTest();
  int data = 0;
  const presonus::mixer::SetupContext context(
      presonus::noaa::OpaqueSetupReference{&data},
      presonus::noaa::OpaqueSetupReference{&data});
  {
    App borrowed(presonus::mixer::setupContextTag, context);
    assert(&borrowed.portableSetupContext() == &context);
    restoreSignalTest();
  }
  return 0;
}

extern "C" void completeDeletingDestructor(MixerApplication *) asm(
    "_ZN8Presonus5Mixer16MixerApplicationD0Ev");

static int destructors(const std::string &variant, bool live) {
  static Offline offline;
  static OfflinePins pins;
  presonus::surface_panel_port::setInputPinConstructionIO(&pins);
  setSpiServiceConstructionIO(&offline);
  Transport network;
  Clock clock;
  trace.reserve(64);
  App *app = new App;
  if (live) {
    auto card = std::make_unique<TCardUCNetHandler>(ucNetHandlerOwnedSetupTag,
                                                    network, clock, true);
    auto &state = card->portableState();
    fill(state.incoming, 1);
    fill(*state.outgoing, 1);
    incomingAddress = &state.incoming;
    outgoingAddress = state.outgoing;
    endpointAddress = card->portableOwnedEndpoint();
    assert(state.channel && endpointAddress);
    selfAddress = card.get();
    TCardSPI::instance().registerReceiver(card.get());
    app->adoptPortableCard(std::move(card));
  }
  applicationAddress = app;
  capture = true;
  if (variant == "D0") {
    // Host GNU/Itanium variant probe on a real derived object without fields.
    static_assert(sizeof(App) == sizeof(MixerApplication));
    completeDeletingDestructor(app);
  } else if (variant == "virtual-delete") {
    MixerApplication *base = app;
    delete base;
  } else if (variant == "D1") {
    app->MixerApplication::~MixerApplication();
  } else {
    assert(variant == "D2");
    app->~App();
  }
  capture = false;
  assert(!selfAddress && !endpointAddress);
  if (variant == "D1" || variant == "D2") {
    assert(applicationAddress == app);
    __real__ZdlPv(app);
    applicationAddress = nullptr;
  }
  assert(!applicationAddress);
  restoreSignalTest();
  emit();
  return 0;
}

int main(int argc, char **argv) {
  assert(argc >= 2);
  const std::string mode = argv[1];
  if (mode == "provider")
    return cardLifecycleReplayMain(argc, argv);
  struct sigaction ignored{};
  ignored.sa_handler = SIG_IGN;
  sigemptyset(&ignored.sa_mask);
  assert(sigaction(SIGINT, &ignored, nullptr) == 0);
  if (mode == "C1" || mode == "C2")
    return constructors();
  if (mode == "network_ready") {
    App app;
    const MixerApplication &base = app;
    const INetworkClientFactory &factory = app;
    std::cout << base.isNetworkClientReady() << ' '
              << factory.isNetworkClientReady() << '\n';
    return 0;
  }
  assert(argc == 3);
  return destructors(mode, std::stoi(argv[2]) != 0);
}
