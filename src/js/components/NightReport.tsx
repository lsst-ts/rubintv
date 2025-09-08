import React, { useState, useEffect } from "react"
import {
  NightReportProps,
  NightReportTabProps,
  NightReportPlot,
  NightReportPlotProps,
  NightReportType,
  NightReportTextProps,
  TabType,
  TextTabType,
} from "./componentTypes"
import { groupBy, sanitiseString } from "../modules/utils"

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

// Simplified: expects a single tab object for text
function NightReportText({ tab, selected }: NightReportTextProps) {
  if (!tab || tab.id !== selected) return null
  const data = tab.data || {}
  return (
    <div
      id={`tabgroup-${tab.id}`}
      className={`tab-content ${tab.id === selected ? "selected" : ""}`}
    >
      {tab.id === "efficiency" ? (
        <ul className="dashboard-text">
          {Object.entries(data)
            .filter(([key]) => key.startsWith("text_"))
            .map(([textName, text]) =>
              text ? (
                <li key={textName}>
                  <MultilineText text={text} />
                </li>
              ) : null
            )}
        </ul>
      ) : (
        <ul>
          {Object.entries(data)
            .filter(([key]) => !key.startsWith("text_"))
            .map(([title, link]) => (
              <li key={link}>
                <a href={link} target="_blank" rel="noreferrer">
                  {title}
                </a>
              </li>
            ))}
        </ul>
      )}
    </div>
  )
}

function NightReportTabs({ tabs, selected, setSelected }: NightReportTabProps) {
  const [hiddenTabs, setHiddenTabs] = useState(["elana"])
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
  }, [typed, hiddenTabs])

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

function NightReportPlots({
  tab,
  selected,
  camera,
  locationName,
  homeUrl,
}: NightReportPlotProps) {
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
function getTabs(nightReport: NightReportType): Array<TabType | TextTabType> {
  const tabs = []
  if (nightReport.text) {
    const hasEfficiency = Object.keys(nightReport.text).some((k) =>
      k.startsWith("text_")
    )
    const hasQA = Object.keys(nightReport.text).some(
      (k) => !k.startsWith("text_")
    )
    if (hasEfficiency) {
      tabs.push({
        id: "efficiency",
        label: "Efficiency",
        type: "text" as const,
        data: nightReport.text,
      })
    }
    if (hasQA) {
      tabs.push({
        id: "qa_plots",
        label: "QA Plots",
        type: "text" as const,
        data: nightReport.text,
      })
    }
  }
  if (nightReport.plots) {
    const grouped = groupBy(nightReport.plots, (plot) => plot.group)
    for (const [group, plots] of grouped) {
      tabs.push({
        id: sanitiseString(group),
        label: group,
        type: "plot" as const,
        data: plots,
      })
    }
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
      localStorage.setItem("night-report-selected", storedSelected)
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
      }
    }
    window.addEventListener("nightreport", handleNightReportEvent as EL)
    return () => {
      window.removeEventListener("nightreport", handleNightReportEvent as EL)
    }
  }, [date])

  if (Object.entries(nightReport).length === 0) {
    return <h3>There is no night report for today yet</h3>
  }

  const selectedTab = tabs.find((tab) => tab.id === selected)

  return (
    <>
      <h3 id="the-date">
        {camera.night_report_label} for: {initialDate}
      </h3>
      <div className="plots-section tabs">
        <NightReportTabs
          tabs={tabs}
          selected={selected}
          setSelected={setSelected}
        />
        <NightReportText
          tab={
            selectedTab && selectedTab.type === "text" ? selectedTab : undefined
          }
          selected={selected}
        />
        <NightReportPlots
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
