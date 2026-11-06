// Compile this header first, without MidiMixerHandler.hpp providing
// declarations.
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <type_traits>
using EncoderDispatch = void (Presonus::Surface::PanelRegistrar::*)(
    const Presonus::Panel::ControlRegistrar &, int, int,
    Presonus::Panel::EncoderControl *);
static_assert(std::is_same_v<
              decltype(&Presonus::Surface::PanelRegistrar::dispatchMidiEncoder),
              EncoderDispatch>);
