import React, { useState, useEffect } from "react"
import {
  NightReportType,
  NightReportProps,
  NightReportTabProps,
  NightReportPlot,
  NightReportPlotsTabProps,
  NightReportTextTabProps,
  TabType,
} from "./componentTypes"
import { groupBy, sanitiseString } from "../modules/utils"
import { DEFAULT_HIDDEN_TABS } from "../config"

type EL = EventListener

// Helper component for rendering multiline text with double-space as &nbsp;&nbsp;
function MultilineText({ text }: { text: string }) {
  if (!text) return null
  return (
    <>
      {text
        .split("\n")
        .map((line, idx) =>
          line ? (
            <p key={idx}>{line.replace(/ {2}/g, "\u00A0\u00A0")}</p>
          ) : (
            <br key={idx} />
          )
        )}
    </>
  )
}

function NightReportTextTab({ tab, selected }: NightReportTextTabProps) {
  if (!tab || tab.id !== selected || tab.type !== "text") return null

  const textItem = tab.data

  if (textItem.type === "multiline") {
    return (
      <div
        id={`tabgroup-${tab.id}`}
        className="tab-content selected monospaced"
      >
        <MultilineText text={textItem.content as string} />
      </div>
    )
  }

  if (textItem.type === "keyvalues") {
    return (
      <div id={`tabgroup-${tab.id}`} className="tab-content selected">
        <ul>
          {Object.entries(textItem.content as Record<string, string>).map(
            ([key, value]) => (
              <li key={key}>
                {key}: {value}
              </li>
            )
          )}
        </ul>
      </div>
    )
  }

  if (textItem.type === "links") {
    return (
      <div id={`tabgroup-${tab.id}`} className="tab-content selected">
        <ul>
          {(textItem.content as Array<{ label: string; url: string }>).map(
            (link) => (
              <li key={link.url}>
                <a
                  href={link.url}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={link.label}
                >
                  {link.label}
                </a>
              </li>
            )
          )}
        </ul>
      </div>
    )
  }

  return null
}

function NightReportTabs({ tabs, selected, setSelected }: NightReportTabProps) {
  const [hiddenTabs, setHiddenTabs] = useState(DEFAULT_HIDDEN_TABS)
  const [typed, setTyped] = useState("")

  useEffect(() => {
    const keyPress = (e: KeyboardEvent) => {
      const newTyped = typed + e.key
      setTyped(newTyped)
      if (hiddenTabs.includes(newTyped)) {
        setSelected(newTyped)
        const newHiddenTabs = hiddenTabs.filter((k) => k !== newTyped)
        setHiddenTabs(newHiddenTabs)
        if (newHiddenTabs.length === 0) {
          document.body.removeEventListener("keydown", keyPress)
        }
      } else {
        const isTypingAnyKey = hiddenTabs.some((k) => k.startsWith(newTyped))
        if (!isTypingAnyKey) {
          setTyped("")
        }
      }
    }
    document.body.addEventListener("keydown", keyPress)
    return () => {
      document.body.removeEventListener("keydown", keyPress)
    }
  }, [typed, hiddenTabs, setSelected])

  const handleSelectionChange = (tabId: string) => {
    setSelected((prevSelected) => {
      if (tabId !== prevSelected) {
        localStorage.setItem("night-report-selected", tabId)
      }
      return tabId
    })
  }

  return (
    <div className="tab-titles">
      {tabs.map((tab) => {
        let isDisabled = "",
          isSelected = ""
        if (hiddenTabs.includes(tab.id)) {
          isDisabled = "disabled"
        }
        if (tab.id === selected) {
          isSelected = "selected"
        }
        return (
          <div
            key={tab.id}
            onClick={() => handleSelectionChange(tab.id)}
            id={`tabtitle-${tab.id}`}
            className={`tab-title ${isDisabled} ${isSelected}`}
          >
            {tab.label}
          </div>
        )
      })}
    </div>
  )
}

function NightReportPlotsTab({
  tab,
  selected,
  camera,
  locationName,
  homeUrl,
}: NightReportPlotsTabProps) {
  if (!tab || tab.id !== selected) return null
  const groupedPlots = tab.data
  return (
    <div
      id={`tabgroup-${tab.id}`}
      className={`tab-content plots-grid selected`}
    >
      {groupedPlots.map((plot: NightReportPlot) => {
        const imgUrl = `${homeUrl}plot_image/${locationName}/${camera.name}/${tab.label}/${plot.filename}`
        return (
          <figure key={plot.hash} className="plot">
            <a href={imgUrl}>
              <img src={imgUrl} alt={plot.filename} />
            </a>
            <figcaption>{plot.filename}</figcaption>
          </figure>
        )
      })}
    </div>
  )
}

// Helper to build tabs array from nightReport
function getTabs(nightReport: NightReportType): TabType[] {
  const tabs: TabType[] = []

  // Add text tabs
  if (nightReport.text) {
    if (!Array.isArray(nightReport.text)) {
      console.warn(
        "nightReport.text is not an array. Skipping text tabs generation.",
        JSON.stringify(nightReport.text)
      )
      return tabs
    }
    nightReport.text.forEach((textItem) => {
      if (!textItem.title || !textItem.type || !textItem.content) {
        console.warn(
          "Skipping invalid night report text item:",
          JSON.stringify(textItem)
        )
        return
      }
      tabs.push({
        id: sanitiseString(textItem.title),
        label: textItem.title,
        type: "text",
        data: textItem,
      })
    })
  }

  // Add plot tabs grouped by group
  if (nightReport.plots) {
    const grouped = groupBy(nightReport.plots, (plot) => plot.group)
    grouped.forEach(([group, plots]) => {
      tabs.push({
        id: sanitiseString(group),
        label: group,
        type: "plot",
        data: plots,
      })
    })
  }

  return tabs
}

function NightReport({
  initialNightReport,
  initialDate,
  camera,
  locationName,
  homeUrl,
}: NightReportProps) {
  const [date, setDate] = useState(initialDate)
  const [nightReport, setNightReport] = useState(initialNightReport)

  const tabs = getTabs(nightReport)
  const [selected, setSelected] = useState(() => {
    const tabIds = tabs.map((tab) => tab.id)
    let storedSelected = localStorage.getItem("night-report-selected")
    if (!storedSelected || !tabIds.includes(storedSelected)) {
      storedSelected = tabIds[0]
      if (storedSelected) {
        localStorage.setItem("night-report-selected", storedSelected)
      }
    }
    return storedSelected
  })

  useEffect(() => {
    function handleNightReportEvent(event: CustomEvent) {
      const { datestamp, data, dataType } = event.detail
      if (datestamp && datestamp !== date) {
        setDate(datestamp)
      }
      if (dataType === "nightReport") {
        setNightReport(data)
        // After updating the night report, validate the selection against new tabs
        const newTabs = getTabs(data)
        const newTabIds = newTabs.map((tab) => tab.id)
        const storedSelected = localStorage.getItem("night-report-selected")

        if (storedSelected && newTabIds.includes(storedSelected)) {
          // Stored selection is still valid in new tabs
          setSelected(storedSelected)
        } else {
          // Stored selection doesn't exist in new tabs, default to first tab
          const defaultSelection = newTabIds[0]
          if (defaultSelection) {
            localStorage.setItem("night-report-selected", defaultSelection)
            setSelected(defaultSelection)
          }
        }
      }
    }
    window.addEventListener("nightreport", handleNightReportEvent as EL)
    return () => {
      window.removeEventListener("nightreport", handleNightReportEvent as EL)
    }
  }, [date])

  if (Object.entries(nightReport).length === 0) {
    return (
      <div className="tabs">
        <h3>There is no {camera.night_report_label} for today yet</h3>
      </div>
    )
  }

  const selectedTab = tabs.find((tab) => tab.id === selected)

  return (
    <>
      <h3 id="the-date">
        {camera.night_report_label} for: {initialDate}
      </h3>
      <div className="tabs">
        <NightReportTabs
          tabs={tabs}
          selected={selected}
          setSelected={setSelected}
        />
        <NightReportTextTab
          tab={
            selectedTab && selectedTab.type === "text" ? selectedTab : undefined
          }
          selected={selected}
        />
        <NightReportPlotsTab
          tab={
            selectedTab && selectedTab.type === "plot" ? selectedTab : undefined
          }
          selected={selected}
          camera={camera}
          locationName={locationName}
          homeUrl={homeUrl}
        />
      </div>
    </>
  )
}

export default NightReport
