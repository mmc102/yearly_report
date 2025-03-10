{-# LANGUAGE OverloadedStrings #-}

module HtmlGenerators.UploadPage (renderUploadPage, renderSelectAccountPage, makeUploadDropzone) where

import Control.Monad (forM_, unless)
import Control.Monad.IO.Class (MonadIO (liftIO))
import Data.List (null)
import qualified Data.List as List
import qualified Data.Map.Strict as Map
import Data.Semigroup (All (getAll))
import Database.Files (getAllProcessedFiles)
import Database.Models
import Database.Persist
import Database.Persist.Postgresql (fromSqlKey)
import Text.Blaze.Html5 as H
import qualified Text.Blaze.Html5 as H
import Text.Blaze.Html5.Attributes as A
import qualified Text.Blaze.Html5.Attributes as A

makeUploadDropzone :: Html
makeUploadDropzone =
  H.div ! A.class_ "w-full max-w-3xl mx-auto text-center" $ do
    H.script ! A.type_ "text/javascript" ! A.src "/upload.js" $ mempty

    -- Page Title
    H.h1 ! A.class_ "text-4xl font-bold text-primary mb-4" $ "Upload Transactions"
    H.p ! A.class_ "text-gray-600 text-lg mb-6" $ "Drag and drop your bank statement PDFs or click to upload."

    -- Upload Form
    H.form
      ! A.action "/upload"
      ! A.method "post"
      ! A.enctype "multipart/form-data"
      ! A.class_ "flex flex-col items-center gap-4"
      $ do
        -- Upload Section (Dropzone)
        H.div
          ! A.class_ "bg-white min-w-96 border-2 border-dashed border-primary rounded-lg p-6 shadow-md flex flex-col items-center cursor-pointer hover:bg-gray-100 transition"
          ! A.id "dropzone"
          ! A.ondragover "handleDragOver(event)"
          ! A.ondrop "handleFileDrop(event)"
          ! A.onclick "triggerFileInput()"
          $ do
            -- Dropzone Instruction
            H.p ! A.class_ "text-gray-700 font-medium mb-2" $ "Click or Drag files here"

            -- File Input (Hidden)
            H.input
              ! A.type_ "file"
              ! A.name "pdfFiles"
              ! A.id "pdfFileInput"
              ! A.class_ "hidden"
              ! A.accept "application/pdf"
              ! A.multiple "multiple"
              ! A.onchange "updateFileList()"

            -- File Preview List
            H.ul ! A.id "fileList" ! A.class_ "text-gray-700 text-sm mt-2" $ ""

        -- Upload Button
        H.button
          ! A.type_ "submit"
          ! A.class_ "primary-button mt-4"
          ! A.id "uploadButton"
          ! A.disabled "disabled"
          $ "Upload Files"

renderUploadPage :: Entity User -> IO Html
renderUploadPage user = do
  files <- getAllProcessedFiles user

  return $ H.div $ do
    makeUploadDropzone
    generateProcessedFilesComponent files

generateProcessedFilesComponent :: [(Entity ProcessFileJob, Entity UploadedPdf, Maybe (Entity TransactionSource))] -> Html
generateProcessedFilesComponent processedFiles = do
  H.div ! A.class_ "mt-2 p-6 bg-white rounded-lg shadow-md" $ do
    if List.null processedFiles
      then H.p ! A.class_ "text-gray-500 text-center" $ "No files have been processed yet."
      else do
        -- Separate files with a TransactionSource from those still processing (Nothing)
        let (processingFiles, categorizedFiles) = List.partition (\(_, _, ts) -> ts == Nothing) processedFiles

        -- Group categorized files by transaction source
        let groupedFiles =
              Map.fromListWith
                (++)
                [ (entityKey src, [(job, file)])
                  | (job, file, Just src) <- categorizedFiles
                ]

        -- Render each transaction source as a section
        forM_ (Map.toList groupedFiles) $ \(sourceId, files) -> do
          let sourceName = transactionSourceName (entityVal (List.head [src | (_, _, Just src) <- processedFiles, entityKey src == sourceId]))

          -- Section Header
          H.div ! A.class_ "mb-6" $ do
            H.h2 ! A.class_ "text-lg font-semibold text-gray-700 mb-2" $ toHtml sourceName

            -- Render Table for categorized files
            renderProcessedFilesTable files

        -- Processing Section (Files with no TransactionSource yet)
        unless (null processingFiles) $ do
          H.div ! A.class_ "mb-6" $ do
            H.h2 ! A.class_ "text-lg font-semibold text-gray-700 mb-2" $ "Processing"

            -- Render Table for files still processing
            renderProcessedFilesTable [(job, file) | (job, file, _) <- processingFiles]

        -- Reprocess All Button
        H.form
          ! A.method "post"
          ! A.action "/reprocess-all"
          ! A.class_ "flex justify-center mt-4"
          $ do
            H.button
              ! A.type_ "submit"
              ! A.class_ "primary-button"
              $ "Reprocess All Files"

-- Helper function to render the processed files table
renderProcessedFilesTable :: [(Entity ProcessFileJob, Entity UploadedPdf)] -> Html
renderProcessedFilesTable files = do
  H.table ! A.class_ "base-table striped-table hover-table border-primary rounded-lg w-full mb-4" $ do
    -- Table Header
    H.thead ! A.class_ "table-head" $ do
      H.tr $ do
        H.th ! A.class_ "table-cell p-2 border border-primary font-semibold" $ "Filename"
        H.th ! A.class_ "table-cell p-2 border border-primary font-semibold" $ "Status"
        H.th ! A.class_ "table-cell p-2 border border-primary font-semibold" $ "Actions"

    -- Table Rows
    H.tbody $ forM_ files $ \(job, file) -> do
      H.tr ! A.class_ "table-row hover:bg-gray-50 transition" $ do
        -- Filename Column
        H.td ! A.class_ "table-cell px-4 py-3" $
          toHtml (uploadedPdfFilename $ entityVal file)

        -- Status Column
        H.td ! A.class_ "table-cell px-4 py-3 font-medium text-gray-700" $
          toHtml $
            show (processFileJobStatus $ entityVal job)

        -- Actions Column
        H.td ! A.class_ "table-cell-center px-4 py-3 flex justify-center items-center gap-4" $ do
          -- Reprocess Button
          H.form
            ! A.method "post"
            ! A.action (H.toValue $ "/reprocess-file/" <> show (fromSqlKey $ entityKey job))
            $ do
              H.input
                ! A.type_ "hidden"
                ! A.name "fId"
                ! A.value (H.toValue $ show (fromSqlKey $ entityKey file))
              H.button
                ! A.type_ "submit"
                ! A.class_ "secondary-button"
                $ "Reprocess"

          -- Delete Button
          H.form
            ! A.method "post"
            ! A.action "/delete-file/"
            $ do
              H.input
                ! A.type_ "hidden"
                ! A.name "fId"
                ! A.value (H.toValue $ show (fromSqlKey $ entityKey file))
              H.button
                ! A.type_ "submit"
                ! A.class_ "secondary-danger-button"
                $ "Delete File and Transactions"

renderSelectAccountPage :: [(Entity UploadedPdf, Maybe (Entity TransactionSource))] -> [Entity TransactionSource] -> Html
renderSelectAccountPage fileRecords transactionSources =
  H.div ! A.class_ "w-full max-w-3xl mx-auto text-center p-6" $ do
    -- Page Title
    H.h1 ! A.class_ "text-4xl font-bold text-primary mb-4" $ "Select a Transaction Source"
    H.p ! A.class_ "text-gray-600 text-lg mb-6" $ "Choose a transaction source for the uploaded files that need one."

    -- Apply to All Dropdown
    H.div ! A.class_ "mb-4 flex items-center justify-center gap-4" $ do
      H.label ! A.for "apply-to-all" ! A.class_ "font-semibold" $ "Apply to all:"
      H.select
        ! A.id "apply-to-all"
        ! A.class_ "border p-2 rounded w-auto"
        $ do
          H.option ! A.value "" $ "Select a source"
          forM_ transactionSources $ \(Entity sourceId source) -> do
            H.option ! A.value (H.toValue (fromSqlKey sourceId)) $ H.toHtml (transactionSourceName source)

    -- Selection Form
    H.form
      ! A.action "/assign-transaction-source"
      ! A.method "post"
      ! A.class_ "flex flex-col items-center gap-4"
      $ do
        -- Table Listing PDFs
        H.table ! A.class_ "w-full border-collapse border border-gray-300 rounded-lg shadow-md" $ do
          H.thead $ H.tr ! A.class_ "bg-gray-200" $ do
            H.th ! A.class_ "p-3 border" $ "File Name"
            H.th ! A.class_ "p-3 border" $ "Transaction Source"

          H.tbody $ forM_ fileRecords $ \(Entity pdfId pdf, maybeSource) -> do
            H.tr ! A.class_ "border" $ do
              -- File Name Column
              H.td ! A.class_ "p-3 border text-left" $ H.toHtml (uploadedPdfFilename pdf)

              -- Transaction Source Selection Column
              H.td ! A.class_ "p-3 border" $ case maybeSource of
                Just (Entity sourceId source) ->
                  -- Show the assigned source as read-only
                  H.p ! A.class_ "text-gray-600" $ H.toHtml (transactionSourceName source)
                Nothing ->
                  -- Show the dropdown for missing configs
                  H.select
                    ! A.name (H.toValue $ "source-" <> show (fromSqlKey pdfId))
                    ! A.class_ "border p-2 rounded w-full transaction-source-dropdown"
                    $ do
                      H.option ! A.value "" $ "Select a source"
                      forM_ transactionSources $ \(Entity sourceId source) -> do
                        H.option ! A.value (H.toValue (fromSqlKey sourceId)) $ H.toHtml (transactionSourceName source)

        -- Submit Button (Only enabled if there are missing configs)
        if any (\(_, maybeSource) -> maybeSource == Nothing) fileRecords
          then H.button ! A.type_ "submit" ! A.class_ "mt-4 primary-button" $ "Save Selection"
          else H.p ! A.class_ "text-gray-600 mt-4" $ "All files already have a transaction source assigned."

    -- JavaScript to Apply Selection to All Dropdowns
    H.script ! A.type_ "text/javascript" $
      H.toHtml
        ( unlines
            [ "document.getElementById('apply-to-all').addEventListener('change', function() {",
              "    var selectedValue = this.value;",
              "    var dropdowns = document.querySelectorAll('.transaction-source-dropdown');",
              "    dropdowns.forEach(function(dropdown) {",
              "        if (dropdown.value === '') {",
              "            dropdown.value = selectedValue;",
              "        }",
              "    });",
              "});"
            ]
        )
