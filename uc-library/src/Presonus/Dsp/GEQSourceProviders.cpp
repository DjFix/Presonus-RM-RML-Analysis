#include "presonus/mixer_dsp/GEQSourceProviders.hpp"
#include "presonus/mixer_dsp/AdditionalFormatters.hpp"
#include <atomic>
#include <mutex>
#include <stdexcept>
namespace {
std::atomic<bool> ready{false};
std::once_flag bootstrap;
class NamedGainSourceFormatter final : public Presonus::Dsp::GainFormatter {
public:
  NamedGainSourceFormatter()
      : Presonus::Dsp::GainFormatter(
            Presonus::Dsp::AdditionalFormatterSourceTag{}, 1, false) {
    // Actual app initializer records precision1,label0 for this name.
    // Tagged source-port adapter; no original Gain constructor/layout claim.
    name = "gain.1.value";
  }
};
struct ProviderObjects {
  NamedGainSourceFormatter gain;
};
ProviderObjects &providers() {
  static ProviderObjects objects;
  return objects;
}
} // namespace
namespace presonus::dsp {
void registerGEQSourcePortProviders() {
  std::call_once(bootstrap, [] {
    auto &objects = providers();
    auto *found = Core::FormatterRegistry::find("gain.1.value");
    if (found && found != &objects.gain)
      throw std::logic_error(
          "GEQ source bootstrap: conflicting formatter name");
    Core::FormatterRegistry::add(&objects.gain);
    if (Core::FormatterRegistry::find("gain.1.value") != &objects.gain)
      throw std::runtime_error(
          "GEQ source bootstrap: registration unavailable");
    ready.store(true, std::memory_order_release);
  });
}
bool geqSourcePortProvidersReady() noexcept {
  return ready.load(std::memory_order_acquire);
}
} // namespace presonus::dsp
