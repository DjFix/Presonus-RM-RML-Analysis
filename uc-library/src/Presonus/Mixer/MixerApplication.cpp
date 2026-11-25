#include "presonus/mixer/setup_property_applications.hpp"

#include "presonus/dsp/OMAPTargetHandler.hpp"
#include "presonus/noaa/ucnet_handler.hpp"
#include <algorithm>
#include <atomic>
#include <cerrno>
#include <mutex>
#include <signal.h>
#include <stdexcept>
#include <system_error>
#include <vector>

namespace Presonus::Mixer {
namespace {
std::atomic<MixerApplication *> currentApplication{nullptr};
std::atomic<bool> quitRequested{false};
static_assert(decltype(quitRequested)::is_always_lock_free);

void requestQuit(int) { quitRequested.store(true, std::memory_order_relaxed); }

struct SignalRegistration {
  std::mutex mutex;
  std::vector<MixerApplication *> applications;
  struct sigaction previous{};
};

SignalRegistration &registration() {
  static SignalRegistration state;
  return state;
}

void enroll(MixerApplication *application) {
  auto &state = registration();
  const std::lock_guard<std::mutex> lock(state.mutex);
  state.applications.push_back(application);
  currentApplication.store(application, std::memory_order_release);
  if (state.applications.size() == 1) {
    struct sigaction action{};
    action.sa_handler = requestQuit;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGINT, &action, &state.previous) != 0) {
      const int error = errno;
      state.applications.pop_back();
      currentApplication.store(nullptr, std::memory_order_release);
      throw std::system_error(error, std::generic_category(),
                              "sigaction(SIGINT)");
    }
  }
}

void retire(MixerApplication *application) {
  auto &state = registration();
  const std::lock_guard<std::mutex> lock(state.mutex);
  auto &applications = state.applications;
  applications.erase(
      std::find(applications.begin(), applications.end(), application));
  currentApplication.store(applications.empty() ? nullptr : applications.back(),
                           std::memory_order_release);
  if (applications.empty()) {
    struct sigaction installed{};
    if (sigaction(SIGINT, nullptr, &installed) == 0 &&
        !(installed.sa_flags & SA_SIGINFO) &&
        installed.sa_handler == requestQuit)
      sigaction(SIGINT, &state.previous, nullptr);
    quitRequested.store(false, std::memory_order_relaxed);
  }
}
} // namespace

struct MixerApplication::LocalState {
  std::unique_ptr<NOAA::TCardUCNetHandler> card;
  Dsp::OMAPTargetHandler target{
      Dsp::OMAPTargetHandler::SourcePortConstruction{}};
  PortableLifecycleDefaults defaults;
};

MixerApplication::MixerApplication() : local_(std::make_unique<LocalState>()) {
  enroll(this);
  local_->defaults.targetWords[0] = 30;
}

MixerApplication::MixerApplication(presonus::mixer::SetupContextTag,
                                   const presonus::mixer::SetupContext &context)
    : context_(&context) {}

MixerApplication::~MixerApplication() noexcept(false) {
  if (local_) {
    retire(this);
    delete local_->card.release();
  }
}

__attribute__((weak)) bool MixerApplication::isNetworkClientReady() const {
  return true;
}

const presonus::mixer::SetupContext &
MixerApplication::portableSetupContext() const {
  if (!context_)
    throw std::logic_error("Mixer setup context is not bound");
  return *context_;
}

const MixerApplication::PortableLifecycleDefaults &
MixerApplication::portableLifecycleDefaults() const {
  if (!local_)
    throw std::logic_error("Mixer local lifecycle is not active");
  return local_->defaults;
}

Dsp::OMAPTargetHandler &MixerApplication::portableOMAPTarget() {
  if (!local_)
    throw std::logic_error("Mixer local lifecycle is not active");
  return local_->target;
}

void MixerApplication::adoptPortableCard(
    std::unique_ptr<NOAA::TCardUCNetHandler> card) {
  if (!local_ || local_->card || !card)
    throw std::logic_error("Cannot adopt the mixer card handler");
  local_->card = std::move(card);
}

MixerApplication *MixerApplication::portableCurrentApplication() noexcept {
  return currentApplication.load(std::memory_order_acquire);
}

bool MixerApplication::consumePortableQuitRequest() noexcept {
  const std::lock_guard<std::mutex> lock(registration().mutex);
  return portableCurrentApplication() == this &&
         quitRequested.exchange(false, std::memory_order_relaxed);
}
} // namespace Presonus::Mixer
