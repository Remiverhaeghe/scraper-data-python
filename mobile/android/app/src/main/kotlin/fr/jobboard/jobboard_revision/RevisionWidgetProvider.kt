package fr.jobboard.jobboard_revision

import android.appwidget.AppWidgetManager
import android.content.Context
import android.content.SharedPreferences
import android.widget.RemoteViews
import es.antonborri.home_widget.HomeWidgetLaunchIntent
import es.antonborri.home_widget.HomeWidgetProvider

// Widget de l'écran d'accueil : lignes préparées par l'application Flutter
// (lib/services/home_widget_service.dart), ouverture de l'application au toucher.
class RevisionWidgetProvider : HomeWidgetProvider() {
    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray,
        widgetData: SharedPreferences,
    ) {
        appWidgetIds.forEach { widgetId ->
            val views = RemoteViews(context.packageName, R.layout.revision_widget).apply {
                setTextViewText(
                    R.id.widget_due,
                    widgetData.getString("due", null) ?: "Ouvrez l'application pour synchroniser",
                )
                setTextViewText(R.id.widget_next, widgetData.getString("next", null) ?: "")
                setOnClickPendingIntent(
                    R.id.widget_root,
                    HomeWidgetLaunchIntent.getActivity(context, MainActivity::class.java),
                )
            }

            appWidgetManager.updateAppWidget(widgetId, views)
        }
    }
}
