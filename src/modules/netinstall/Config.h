/*
 *   SPDX-FileCopyrightText: 2016 Luca Giambonini <almack@chakraos.org>
 *   SPDX-FileCopyrightText: 2016 Lisa Vitolo     <shainer@chakraos.org>
 *   SPDX-FileCopyrightText: 2017 Kyle Robbertze  <krobbertze@gmail.com>
 *   SPDX-FileCopyrightText: 2017-2018 2020, Adriaan de Groot <groot@kde.org>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

#ifndef NETINSTALL_CONFIG_H
#define NETINSTALL_CONFIG_H

#include "PackageModel.h"

#include "locale/TranslatableConfiguration.h"
#include "modulesystem/InstanceKey.h"

#include <QFutureWatcher>
#include <QObject>
#include <QVariantMap>

#include <memory>

class LoaderQueue;

class Config : public QObject
{
    Q_OBJECT

    Q_PROPERTY( PackageModel* packageModel MEMBER m_model FINAL )
    Q_PROPERTY( QString status READ status NOTIFY statusChanged FINAL )

    // Translations, of the module name (for sidebar) and above the list
    Q_PROPERTY( QString sidebarLabel READ sidebarLabel NOTIFY sidebarLabelChanged FINAL )
    Q_PROPERTY( QString titleLabel READ titleLabel NOTIFY titleLabelChanged FINAL )

public:
    Config( QObject* parent = nullptr );
    ~Config() override;

    void setConfigurationMap( const QVariantMap& configurationMap );

    enum class Status
    {
        Ok,
        FailedBadConfiguration,
        FailedInternalError,
        FailedNetworkError,
        FailedBadData,
        FailedNoData,
        // Larch: distinct from FailedNetworkError, which means the
        // *group list itself* failed to load over the network. This
        // groupsUrl is "local" (no network needed to show the page at
        // all), but the packages a user picks here still need real
        // network access to actually install later -- packages.conf's
        // skip_if_no_internet silently skips the whole packages job
        // offline, so without this, a selection here just silently
        // never installs, with no warning at all.
        NoInternet
    };

    /// Human-readable, translated representation of the status
    QString status() const;
    /// Internal code for the status
    Status statusCode() const { return m_status; }
    void setStatus( Status s );

    /** @brief Re-checks internet connectivity and updates status accordingly.
     *
     * Call each time this page becomes active, not just once at startup --
     * connectivity may have changed since an earlier page (e.g. welcome)
     * checked it. Only overrides status when it's currently Ok or
     * NoInternet, so it won't clobber some other real failure (bad
     * configuration, bad data, etc).
     *
     * Runs a *fresh* probe (Manager::checkHasInternet()) on a worker
     * thread, not Manager::hasInternet()'s cached flag -- that flag is
     * only ever set once, by welcome's own startup check, and never
     * updated again on its own. Without a real re-probe here, connecting
     * to a network after starting the installer offline would never be
     * noticed: this page would keep showing NoInternet forever, no matter
     * how many times it's revisited. Off the GUI thread because the probe
     * itself can block for seconds (see Manager.cpp's own timeout notes).
     */
    void checkInternet();

    bool required() const { return m_required; }
    void setRequired( bool r ) { m_required = r; }

    PackageModel* model() const { return m_model; }

    QString sidebarLabel() const;
    QString titleLabel() const;

    /** @brief Fill model from parsed data.
     *
     * Fills the model with a list of groups -- which can contain
     * subgroups and packages -- from @p groupData.
     */
    void loadGroupList( const QVariantList& groupData );

    /** @brief Write the selected package lists to global storage
     *
     * Since the config doesn't know what module it is for,
     * pass in an instance key.
     */
    void finalizeGlobalStorage( const Calamares::ModuleSystem::InstanceKey& key );

Q_SIGNALS:
    void statusChanged( QString status );  ///< Something changed
    void sidebarLabelChanged( QString label );
    void titleLabelChanged( QString label );
    void statusReady();  ///< Loading groups is complete

private Q_SLOTS:
    void retranslate();
    void loadingDone();
    void internetCheckFinished();

private:
    Calamares::Locale::TranslatedString* m_sidebarLabel = nullptr;  // As it appears in the sidebar
    Calamares::Locale::TranslatedString* m_titleLabel = nullptr;
    PackageModel* m_model = nullptr;
    LoaderQueue* m_queue = nullptr;
    Status m_status = Status::Ok;
    bool m_required = false;
    QFutureWatcher< bool >* m_internetCheckWatcher = nullptr;
};

#endif
