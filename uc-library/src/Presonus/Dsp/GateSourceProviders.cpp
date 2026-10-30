#include "presonus/mixer_dsp/GateSourceProviders.hpp"
#include "core/public/corestringbuffer.h"
#include "presonus/mixer_dsp/CompressorSourceProviders.hpp"
#include "presonus/mixer_dsp/EqSourceProviders.hpp"
#include "presonus/mixer_dsp/GateMeterInterpolators.hpp"
#include "presonus/mixer_dsp/Interpolators.hpp"
#include "presonus/uc/OnOff.hpp"
#include <atomic>
#include <cstring>
#include <memory>
#include <mutex>
#include <stdexcept>
namespace {
std::atomic<bool> gateReady{false};
std::once_flag gateBootstrapOnce;
struct GateProviderObjects {
  Core::CStringBuffer<32> on, off;
  Presonus::UC::Format::OnOff formatter;
  GateProviderObjects(const char *a, const char *b)
      : on(a), off(b), formatter("onoff", on.str(), off.str()) {}
};
GateProviderObjects &gateProviders(const char *a, const char *b) {
  static GateProviderObjects gateObjects(a, b);
  return gateObjects;
}
Core::Interpolator *createSourceGateRange() {
  return new Presonus::Dsp::GateRangeInterpolator;
}
Core::Interpolator *createSourceExp() {
  // Independent modern initial Gate range, not an original Exp constructor or
  // default-state claim. Actual app setRange supplies this same observed range
  // again. Configure before exposing the factory object for direct use.
  const presonus::dsp::InterpolationState seed{0.f, 1.f, .5f, 0.f,
                                               1.f, 1.f, 1.f, 1.f};
  auto result = std::make_unique<Presonus::Dsp::ExpInterpolator>(
      presonus::dsp::InterpolationPortTag{}, seed);
  result->setRange(.00002f, .5f, .005f);
  return result.release();
}
void validateLabel(const char *text) {
  if (!text || std::strlen(text) > 31)
    throw std::invalid_argument(
        "Gate source labels require nonnull <=31 bytes");
  for (const unsigned char *p = reinterpret_cast<const unsigned char *>(text);
       *p; ++p)
    if (*p > 127)
      throw std::invalid_argument("Gate source labels require ASCII");
}
} // namespace
namespace presonus::dsp {
void registerGateSourcePortProviders(const char *onLabel,
                                     const char *offLabel) {
  validateLabel(onLabel);
  validateLabel(offLabel);
  if (!eqSourcePortProvidersReady() || !compressorSourcePortProvidersReady())
    throw std::logic_error(
        "Gate bootstrap requires EQ and Compressor providers");
  auto &objects = gateProviders(onLabel, offLabel);
  if (std::strcmp(onLabel, objects.on.str()) ||
      std::strcmp(offLabel, objects.off.str()))
    throw std::logic_error("Gate bootstrap label configuration changed");
  std::call_once(gateBootstrapOnce, [&objects] {
    // Actual CCL API cannot inspect unknown callback validity. As for existing
    // bootstraps, serialized setup, valid nonnull factories and successful
    // allocation are prerequisites; this is not an OOM rollback transaction.
    if (Core::FormatterRegistry::find("onoff"))
      throw std::logic_error("Gate bootstrap: conflicting onoff formatter");
    std::unique_ptr<Core::Interpolator> oldExp(
        Core::InterpolatorFactory::create("exp"));
    std::unique_ptr<Core::Interpolator> oldGateRange(
        Core::InterpolatorFactory::create("gaterange"));
    if (oldExp || oldGateRange)
      throw std::logic_error(
          "Gate bootstrap: conflicting interpolation factory");
    Core::FormatterRegistry::add(&objects.formatter);
    Core::InterpolatorFactory::add("exp", createSourceExp);
    Core::InterpolatorFactory::add("gaterange", createSourceGateRange);
    std::unique_ptr<Core::Interpolator> exp(
        Core::InterpolatorFactory::create("exp"));
    std::unique_ptr<Core::Interpolator> gateRange(
        Core::InterpolatorFactory::create("gaterange"));
    if (!exp || !gateRange ||
        Core::FormatterRegistry::find("onoff") != &objects.formatter)
      throw std::runtime_error("Gate source registration unavailable");
    gateReady.store(true, std::memory_order_release);
  });
}
bool gateSourcePortProvidersReady() noexcept {
  return gateReady.load(std::memory_order_acquire);
}
} // namespace presonus::dsp
