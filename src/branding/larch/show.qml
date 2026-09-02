import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation
{
    id: presentation

    function nextSlide() {
        presentation.goToNextSlide();
    }

    Timer {
        id: advanceTimer
        interval: 6000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: nextSlide()
    }

    Slide {
        centeredText: qsTr("<h2>Larch</h2>" +
                            "Distro for lazy yet power users.")
    }

    Slide {
        centeredText: qsTr("<h2>niri + noctalia, out of the box</h2>" +
                            "A scrollable-tiling Wayland compositor paired with a " +
                            "Quickshell-based desktop shell, configured and ready to go.")
    }

    Slide {
        centeredText: qsTr("<h2>Stock Arch underneath</h2>" +
                            "No custom package repository to trust or distrust. " +
                            "Everything comes straight from Arch's own repos.")
    }

    Slide {
        centeredText: qsTr("<h2>Almost there</h2>" +
                            "Sit back while Larch installs.")
    }

    function onActivate() {
        presentation.currentSlide = 0;
    }

    function onLeave() {
    }

}
