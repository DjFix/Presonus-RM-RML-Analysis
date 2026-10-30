#include "presonus/mixer_dsp/CompressorSourceProviders.hpp"
#include "presonus/mixer_dsp/EqSourceProviders.hpp"
#include "presonus/mixer_dsp/Formatters.hpp"
#include "presonus/mixer_dsp/Interpolators.hpp"
#include <atomic>
#include <memory>
#include <mutex>
#include <stdexcept>
namespace {
std::atomic<bool> compressorReady{false};
std::once_flag compressorBootstrapOnce;
// Independent adapter over actual admitted code/Core::Formatter field; this
// does not recover or claim the original RatioFormatter default constructor.
class NamedRatioSourceFormatter final : public Presonus::Dsp::RatioFormatter {
public:
  NamedRatioSourceFormatter()
      : Presonus::Dsp::RatioFormatter(Presonus::Dsp::FormatterSourceTag{}) {
    name = "ratio";
  }
};
struct CompressorProviderObjects {
  Presonus::Dsp::TimeFormatter time;
  NamedRatioSourceFormatter ratio;
};
CompressorProviderObjects &compressorProviders() {
  static CompressorProviderObjects compressorObjects;
  return compressorObjects;
}
Core::Interpolator *createSourceRatio() {
  // Independent valid source-port seed. Actual setRange(1,20,2) follows in
  // the original descriptor construction; no original Ratio C1 claim.
  const presonus::dsp::InterpolationState seed{1.f,  20.f, 2.f, 0.f,
                                               .95f, -1.f, 0.f, 0.f};
  return new Presonus::Dsp::RatioInterpolator(
      presonus::dsp::InterpolationPortTag{}, seed);
}
} // namespace
namespace presonus::dsp {
void registerCompressorSourcePortProviders() {
  if (!eqSourcePortProvidersReady())
    throw std::logic_error(
        "Compressor bootstrap requires existing EQ source bootstrap");
  std::call_once(compressorBootstrapOnce, [] {
    auto &objects = compressorProviders();
    // Core registry APIs expose no generic callback/type inspection. Setup is
    // serialized, allocation succeeds and existing factories return nonnull.
    // Unknown preexisting names are conservatively rejected before
    // registration.
    if (Core::FormatterRegistry::find("time") ||
        Core::FormatterRegistry::find("ratio"))
      throw std::logic_error(
          "Compressor bootstrap: conflicting formatter name");
    // Base ratio is absent, so missing slash-name lookup cannot create a
    // wrapper.
    if (Core::FormatterRegistry::find("ratio/~/limit"))
      throw std::logic_error(
          "Compressor bootstrap: conflicting range formatter");
    std::unique_ptr<Core::Interpolator> oldRatio(
        Core::InterpolatorFactory::create("ratio"));
    if (oldRatio)
      throw std::logic_error("Compressor bootstrap: conflicting ratio factory");
    Core::FormatterRegistry::add(&objects.time);
    Core::FormatterRegistry::add(&objects.ratio);
    Core::InterpolatorFactory::add("ratio", createSourceRatio);
    std::unique_ptr<Core::Interpolator> ratio(
        Core::InterpolatorFactory::create("ratio"));
    if (!ratio || Core::FormatterRegistry::find("time") != &objects.time ||
        Core::FormatterRegistry::find("ratio") != &objects.ratio)
      throw std::runtime_error(
          "Compressor bootstrap: actual provider registration unavailable");
    compressorReady.store(true, std::memory_order_release);
  });
}
bool compressorSourcePortProvidersReady() noexcept {
  return compressorReady.load(std::memory_order_acquire);
}
} // namespace presonus::dsp
