#include "presonus/application/ResourceLibrary.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/noaa/card.hpp"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/status_property.hpp"
#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <string>

using namespace Presonus::NOAA;
using namespace presonus::noaa;

namespace {
struct Response final : presonus::dice::ResponseServices {
  std::int64_t clockRawTicks() override { std::abort(); }
  void pumpIdle(bool) override { std::abort(); }
  void sleepMilliseconds(std::uint32_t) override { std::abort(); }
  void timeoutNotice(bool, std::uint32_t, std::uint32_t) override {
    std::abort();
  }
};
struct IO final : SpiServiceIO {
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int, const SpiTransfer &) override { std::abort(); }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { std::abort(); }
  void diagnostic(bool, const char *, int, bool) override { std::abort(); }
};
struct Card final : TCard {
  Card(CardState &state, Response &response, IO &io)
      : TCard(cardSetupTag, state, response, io) {}
  std::int32_t updateFirmware(Presonus::UC::IFirmwareUpdateListener *,
                              int) override {
    std::abort();
  }
};
struct Handler final : TCardHandler {
  Handler(CardHandlerState &state, Response &response, bool respond)
      : TCardHandler(cardHandlerSetupTag, state, response), state(state),
        respond(respond) {}
  void getProperty(Core::Property &request) override {
    const auto *status = state.statusProperty;
    if (status != &request || request.type != NOAAStatusProperty::kID ||
        request.size != 60 ||
        !std::all_of(status->payload.begin(), status->payload.end(),
                     [](unsigned char b) { return b == 0; }))
      std::abort();
    ++calls;
    if (respond)
      TCardHandler::getProperty(request);
    std::memcpy(&observedMode, status->payload.data(), sizeof(observedMode));
  }
  void setProperty(const Core::Property &) override { std::abort(); }
  void release() override { std::abort(); }
  int threadEntry() override { std::abort(); }

  CardHandlerState &state;
  bool respond;
  int calls = 0;
  std::uint32_t observedMode = 0;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const std::string mode(argv[1]);
  const bool respond = mode != "none";
  Presonus::ResourceLibrary resources;
  CardState cardState{};
  cardState.resources = &resources;
  cardState.observedWord14 = respond ? std::stoul(mode) : 0;
  Response response;
  IO io;
  Card card(cardState, response, io);
  std::array<unsigned char, 52> seed;
  seed.fill(0xa7);
  NOAAStatusProperty status(seed);
  CardHandlerState state{card};
  state.statusProperty = &status;
  Handler handler(state, response, respond);
  Presonus::Mixer::MixerComponentBase mixer;
  mixer.digitalRouteHandler = &handler;
  mixer.serialStatus = &status;
  const bool result = mixer.hasDanteInputRoutes();
  if (status.payload != seed || state.statusProperty != &status)
    return 3;
  std::cout << "status " << result << ' ' << handler.calls << ' '
            << handler.observedMode << '\n';
}
